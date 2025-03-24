from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_session import Session
import libvirt
import os
import time
from xml.etree import ElementTree as ET
from functools import wraps
from pam import pam

app = Flask(__name__)
app.secret_key = 'a3f7cbd349e6a215d9c95ea3a882b3746cd7b2f14e36fda3ac89e4f35ef4503f'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.permanent_session_lifetime = timedelta(minutes=30)
Session(app)

auth = pam()

def _auth_callback(credentials, user_data):
    for cred in credentials:
        if cred[0] == libvirt.VIR_CRED_PASSPHRASE:
            cred[4] = session.get('password')
        elif cred[0] == libvirt.VIR_CRED_AUTHNAME:
            cred[4] = session.get('username', 'root')
    return 0

def connect():
    if 'uri' not in session or 'password' not in session:
        return None
    try:
        auth_data = [
            [libvirt.VIR_CRED_AUTHNAME, libvirt.VIR_CRED_PASSPHRASE],
            _auth_callback,
            None
        ]
        conn = libvirt.openAuth(session['uri'], auth_data, 0)
        if conn is None:
            raise libvirt.libvirtError("Connexion échouée : libvirt.openAuth() a retourné None")
        return conn
    except libvirt.libvirtError as e:
        print(f"[!] Erreur de connexion : {e}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'host' not in session or 'password' not in session or 'uri' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        host = request.form['host'].strip()
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        # Authentification système via PAM
        if not auth.authenticate(username, password):
            flash("Échec d'authentification système.", "danger")
            return render_template('login.html')

        uri = f"qemu+ssh://{username}@{host}/system"

        session['host'] = host
        session['username'] = username
        session['password'] = password
        session['uri'] = uri

        conn = connect()
        if conn:
            conn.close()
            flash("Connexion réussie.", "success")
            return redirect(url_for('index'))
        else:
            session.clear()
            flash("Échec de connexion à libvirt.", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Déconnecté avec succès.", "success")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return redirect(url_for('list_vms'))

@app.route('/vms')
@login_required
def list_vms():
    conn = connect()
    if not conn:
        flash("Connexion échouée.", "danger")
        return redirect(url_for('login'))

    vms = []

    for id in conn.listDomainsID():
        dom = conn.lookupByID(id)
        info = dom.info()
        state_code = info[0]
        is_paused = state_code == libvirt.VIR_DOMAIN_PAUSED
        can_restore = os.path.exists(f"/var/lib/libvirt/qemu/save/{dom.name()}.img")
        vms.append({
            'name': dom.name(), 'id': id, 'state': 'Actif',
            'memory': info[2], 'maxMemory': info[1], 'vcpus': info[3],
            'is_paused': is_paused, 'can_restore': can_restore
        })

    for name in conn.listDefinedDomains():
        dom = conn.lookupByName(name)
        can_restore = os.path.exists(f"/var/lib/libvirt/qemu/save/{name}.img")
        vms.append({
            'name': name, 'id': '-', 'state': 'Inactif',
            'memory': '-', 'maxMemory': '-', 'vcpus': '-',
            'is_paused': False, 'can_restore': can_restore
        })

    conn.close()
    return render_template('vms.html', vms=vms)

@app.route('/vm/<name>/start')
@login_required
def start_vm(name):
    conn = connect()
    dom = conn.lookupByName(name)
    try:
        dom.create()
        flash(f"VM '{name}' démarrée.", "success")
    except:
        flash(f"Erreur au démarrage de '{name}'.", "danger")
    conn.close()
    return redirect(url_for('list_vms'))

@app.route('/vm/<name>/stop')
@login_required
def stop_vm(name):
    conn = connect()
    dom = conn.lookupByName(name)
    try:
        dom.destroy()
        flash(f"VM '{name}' arrêtée.", "success")
    except:
        flash(f"Erreur à l'arrêt de '{name}'.", "danger")
    conn.close()
    return redirect(url_for('list_vms'))

@app.route('/vm/<name>/pause')
@login_required
def pause_vm(name):
    conn = connect()
    if not conn:
        flash("Connexion échouée à l'hyperviseur.", "danger")
        return redirect(url_for('list_vms'))
    try:
        dom = conn.lookupByName(name)
        if dom.isActive():
            dom.suspend()
            time.sleep(0.5)
            flash(f"VM '{name}' mise en pause.", "info")
        else:
            flash("Impossible de mettre en pause une VM éteinte.", "warning")
    except libvirt.libvirtError as e:
        flash(f"Erreur lors de la mise en pause de '{name}' : {e}", "danger")
    conn.close()
    return redirect(url_for('list_vms'))

@app.route('/vm/<name>/resume')
@login_required
def resume_vm(name):
    conn = connect()
    dom = conn.lookupByName(name)
    try:
        dom.resume()
        flash(f"VM '{name}' reprise avec succès.", "success")
    except:
        flash(f"Erreur lors de la reprise de '{name}'.", "danger")
    conn.close()
    return redirect(url_for('list_vms'))

@app.route('/vm/<name>/save')
@login_required
def save_vm(name):
    conn = connect()
    dom = conn.lookupByName(name)
    save_path = f"/var/lib/libvirt/qemu/save/{name}.img"
    try:
        dom.save(save_path)
        flash(f"VM '{name}' sauvegardée dans {save_path}.", "success")
    except:
        flash(f"Erreur lors de la sauvegarde de '{name}'.", "danger")
    conn.close()
    return redirect(url_for('list_vms'))

@app.route('/vm/<name>/restore')
@login_required
def restore_vm(name):
    conn = connect()
    save_path = f"/var/lib/libvirt/qemu/save/{name}.img"
    try:
        conn.restore(save_path)
        flash(f"VM '{name}' restaurée depuis {save_path}.", "success")
    except:
        flash(f"Erreur lors de la restauration de '{name}'.", "danger")
    conn.close()
    return redirect(url_for('list_vms'))

@app.route('/vm/<name>/delete')
@login_required
def delete_vm(name):
    conn = connect()
    dom = conn.lookupByName(name)
    try:
        if dom.isActive():
            dom.destroy()
        dom.undefine()
        flash(f"VM '{name}' supprimée.", "success")
    except:
        flash(f"Erreur lors de la suppression de '{name}'.", "danger")
    conn.close()
    return redirect(url_for('list_vms'))

@app.route('/vm/create', methods=['GET', 'POST'])
@login_required
def create_vm():
    if request.method == 'POST':
        name = request.form['name']
        memory = request.form['memory']
        vcpu = request.form['vcpu']
        disksize = request.form['disksize']
        iso = request.form.get('iso', '').strip()

        diskpath = f"/var/lib/libvirt/images/{name}.qcow2"
        os.system(f"qemu-img create -f qcow2 {diskpath} {disksize}G")

        cdrom_xml = f"""
        <disk type='file' device='cdrom'>
          <driver name='qemu' type='raw'/>
          <source file='{iso}'/>
          <target dev='hdc' bus='ide'/>
          <readonly/>
        </disk>
        """ if iso else ""

        xml = f"""
        <domain type='kvm'>
          <name>{name}</name>
          <memory unit='MiB'>{memory}</memory>
          <vcpu>{vcpu}</vcpu>
          <os>
            <type arch='x86_64'>hvm</type>
            <boot dev='cdrom'/>
            <boot dev='hd'/>
          </os>
          <devices>
            <emulator>/usr/bin/qemu-system-x86_64</emulator>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2'/>
              <source file='{diskpath}'/>
              <target dev='vda' bus='virtio'/>
            </disk>
            {cdrom_xml}
            <interface type='network'>
              <source network='default'/>
              <model type='virtio'/>
            </interface>
            <graphics type='vnc' port='-1'/>
          </devices>
        </domain>
        """

        conn = connect()
        try:
            conn.defineXML(xml)
            flash("VM créée avec succès.", "success")
        except Exception as e:
            flash(f"Erreur lors de la création : {e}", "danger")
        conn.close()
        return redirect(url_for('list_vms'))

    return render_template('create_vm.html')

@app.route('/vm/<name>/edit', methods=['GET', 'POST'])
@login_required
def edit_vm(name):
    conn = connect()
    if not conn:
        flash("Connexion échouée.", "danger")
        return redirect(url_for('list_vms'))

    try:
        dom = conn.lookupByName(name)
    except libvirt.libvirtError:
        flash(f"VM '{name}' introuvable.", "danger")
        conn.close()
        return redirect(url_for('list_vms'))

    if dom.isActive():
        flash("Veuillez arrêter la VM avant de la modifier.", "warning")
        conn.close()
        return redirect(url_for('list_vms'))

    if request.method == 'POST':
        try:
            new_memory = int(request.form['memory']) * 1024
            new_vcpu = int(request.form['vcpu'])

            xml = dom.XMLDesc()
            tree = ET.fromstring(xml)

            memory_elem = tree.find('memory')
            if memory_elem is not None:
                memory_elem.text = str(new_memory)

            vcpu_elem = tree.find('vcpu')
            if vcpu_elem is not None:
                vcpu_elem.text = str(new_vcpu)

            new_xml = ET.tostring(tree, encoding='unicode')
            conn.defineXML(new_xml)
            flash(f"VM '{name}' modifiée avec succès.", "success")
        except Exception as e:
            flash(f"Erreur lors de la modification : {e}", "danger")
        conn.close()
        return redirect(url_for('list_vms'))

    try:
        info = dom.info()
        current_memory = info[1] // 1024
        current_vcpu = info[3]
    except:
        current_memory = 512
        current_vcpu = 1
        flash("Impossible de récupérer les infos actuelles.", "warning")

    conn.close()
    return render_template('edit_vm.html', name=name, memory=current_memory, vcpu=current_vcpu)

if __name__ == '__main__':
    app.run(debug=True)

