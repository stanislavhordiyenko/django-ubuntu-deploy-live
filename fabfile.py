import os
import sys
import time
import json

import sensitive

from digitalocean import ClientV2

from fabric.api import env, local, run, put, sudo, prefix, hide, settings, cd, get, lcd
from fabric.colors import red, green
from fabric.operations import prompt


def deploy():
    print("Executing on %(host)s as %(user)s" % env)

    # re-create the destination folder
    local('rm -rf ./dist')
    local('mkdir dist')

    # copy source code to the destination folder
    local('cp -R ./data ./dist/')
    local('cp -R ./public ./dist/')
    local('cp -R ./src ./dist/')
    local('cp -R ./conf ./dist/')
    local('cp ./deploy.sh ./dist/')

    # create necessary folders
    local('mkdir ./dist/bin')
    local('mkdir ./dist/sys')
    local('mkdir ./dist/sys/logs')
    local('mkdir ./dist/sys/socks')

    # remove unused files
    local('rm ./dist/src/db.sqlite3')

    # archive whole website
    local('cd ./dist && tar -zcvf your.domain.com.tar.gz ./')

    if env.name == 'live':
        do_deploy()
        enable_firewall()
    elif env.name == 'staging':
        do_deploy()
        enable_firewall()
        test()
    else:
        vagrant_destroy()
        vagrant_up()
        vagrant_deploy()
        enable_firewall()

    local('rm -rf ./dist')

def dev():
    env.user = 'vagrant'
    env.password = 'vagrant'
    env.hosts = ['127.0.0.1:2222', ]
    env.name = 'dev'

def vagrant_up():
    with hide('output', 'running', 'warnings'), settings(warn_only=True):
        with prefix('export VAGRANT_CWD=$(pwd)'):
            local('vagrant up')

def vagrant_deploy():
    with cd('/home/vagrant'):
        put('./dist/your.domain.com.tar.gz', '/home/vagrant')

        sudo('mkdir your.domain.com && tar -zxvf ./your.domain.com.tar.gz -C ./your.domain.com')
        sudo('mkdir -p /www/your.domain.com')
        sudo('mv /home/vagrant/your.domain.com /www')
        sudo('chmod +x /www/your.domain.com/deploy.sh')

        # execute deploy shell script
        sudo('/www/your.domain.com/deploy.sh')

        # cleanup after the deployment
        sudo('rm /www/your.domain.com/deploy.sh')
        sudo('rm /home/vagrant/your.domain.com.tar.gz')

def vagrant_destroy():
    with hide('output', 'running', 'warnings'), settings(warn_only=True):
        local('vagrant destroy -f')
        local('rm -r .vagrant')

def enable_firewall():
    with hide('output', 'running'), settings(warn_only=True):
        with settings(user="user_name"):
            sudo('apt-get install -y ufw')

            sudo('ufw default deny')
            sudo('ufw logging on')
            sudo('ufw allow 22')
            sudo('ufw allow 80')
            sudo('ufw allow 443')
            sudo('ufw limit ssh/tcp')

            sudo('yes | ufw enable')

def print_json_nicely(j):
    print json.dumps(j, indent=4)

def test():
    import requests

    headers = {
        'X-Auth-Email': '',
        'X-Auth-Key': ''
        }

    def _rest_api_post(resource, **body):
        r = requests.post('https://api.cloudflare.com/client/v4' + resource, headers=headers, data=json.dumps(body))
        return {
            'status_code': r.status_code,
            'json': r.json(),
            'text': r.text,
        }

    def _rest_api_get(resource, query_string=""):
        r = requests.get('https://api.cloudflare.com/client/v4' + resource + query_string, headers=headers)
        return {
            'status_code': r.status_code,
            'json': r.json(),
        }

    def _rest_api_delete(resource, **body):
        r = requests.delete('https://api.cloudflare.com/client/v4' + resource, headers=headers, data=json.dumps(body))
        return {
            'status_code': r.status_code,
            'json': r.json(),
        }

    def cloudflare_get_zone_id(zone_name):
        """Return zone id by zone name.
        """
        r = _rest_api_get('/zones')
        for zone in r["json"]["result"]:
            if zone['name'] == zone_name:
                return zone['id']
        return None

    def cloudflare_get_all_zone_ids():
        r = _rest_api_get('/zones')
        zones = []
        for zone in r["json"]["result"]:
            zones.append(zone['id'])
            print zone['name']
        return zones

    def cloudflare_purge_all_cache(zone_name):
        zone_id = cloudflare_get_zone_id(zone_name)
        r = _rest_api_delete('/zones/%s/purge_cache' % zone_id, purge_everything=True)
        return r['status_code'] == 200

    def cloudflare_get_dns_record_id(zone_name, name):
        zone_id = cloudflare_get_zone_id(zone_name)
        r = _rest_api_get('/zones/%s/dns_records' % zone_id)
        for dns_record in r['json']['result']:
            if dns_record['name'] == name:
                return dns_record['id']

    def cloudflare_add_dns_record(zone_name, name, ip_address):
        zone_id = cloudflare_get_zone_id(zone_name)
        r = _rest_api_post('/zones/%s/dns_records' % zone_id, type="A", name=name, content=ip_address)
        return r['status_code']

    def cloudflare_dns_record_exists(zone_name, name):
        zone_id = cloudflare_get_zone_id(zone_name)
        r = _rest_api_get('/zones/%s/dns_records' % zone_id)
        return name in [dns_record['name'] for dns_record in r['json']['result']]

    def cloudflare_remove_dns_record(zone_name, name):
        """Name should be a full domain, i.e. staging.your.domain.com
        """
        zone_id = cloudflare_get_zone_id(zone_name)
        dns_record_id = cloudflare_get_dns_record_id(zone_name, name)
        r = _rest_api_delete('/zones/%s/dns_records/%s' % (zone_id, dns_record_id, ))
        return r['status_code'] == 200

    host = env.host_string

    if cloudflare_dns_record_exists("your.domain.com", "staging.your.domain.com"):
        cloudflare_remove_dns_record("your.domain.com", "staging.your.domain.com")
        cloudflare_add_dns_record("your.domain.com", "staging.your.domain.com", host)


def staging():
    version = prompt("Please specify the website's version: ")

    client = ClientV2(token=sensitive.DIGITAOCEAN_API_TOKEN)

    # images = client.images.all()

    # for image in images["images"]:
    #     print(image['slug'] + ": %s" % image['id'])

    # sys.exit()

    ssh_key_id = client.keys.all()['ssh_keys'][0]['id']
    droplet = client.droplets.create(name='your.domain.com-v' + version, region='sfo1', size='512mb', image=14169868, ssh_keys=ssh_key_id)
    droplet_id = droplet['droplet']['id']

    ip_address = None

    timeout = time.time() + 60*2
    while True:
        time.sleep(5)
        droplet_info = client.droplets.get(droplet_id=droplet_id)

        if droplet_info['droplet']['status'] == 'active':
            ip_address = droplet_info['droplet']['networks']['v4'][0]['ip_address']
            break;

        if time.time() > timeout:
            print red('Droplet were not created within two minutes in DigitalOcean.')
            sys.exit()

    time.sleep(60)

    env.user = 'root'
    env.password = None
    env.host_string = ip_address
    env.key_filename = '~/.ssh/id_rsa'
    env.name = 'staging'

    print(green("Droplet has been created successfully."))
    print("It's ip address: " + ip_address)

def user_name():
    env.user = 'user_name'
    env.password = 'user_password'

def live():
    host = prompt('Please specify live server: ')

    env.user = 'user_name'
    env.password = 'user_password'
    env.hosts = [host, ]
    env.name = 'live'

def do_deploy():
    with settings(user="root"), cd('/home'):
        put('./dist/your.domain.com.tar.gz', '/home')

        # extract archive
        sudo('mkdir your.domain.com && tar -zxvf ./your.domain.com.tar.gz -C ./your.domain.com')
        sudo('mkdir -p /www/your.domain.com')

        sudo('mv /home/your.domain.com /www')
        sudo('chmod +x /www/your.domain.com/deploy.sh')
        sudo('/www/your.domain.com/deploy.sh')

        sudo('rm /www/your.domain.com/deploy.sh')
        sudo('rm /home/your.domain.com.tar.gz')


def reset_cache():
    with hide('output', 'running'), settings(warn_only=True):
        with settings(user="user_name"):
            sudo('redis-cli flushdb')
            sudo('redis-cli flushall')


def make_backup():
    backup_path = os.path.dirname(os.path.realpath(__file__)) + '/backup'
    local('rm -rf '+ backup_path)
    local('mkdir ' + backup_path)

    with hide('output', 'running'), settings(warn_only=True):
        with settings(user="user_name"):
            with cd('/www/your.domain.com/'), prefix('source ./sys/.venv/bin/activate'):
                sudo('rm -f ./data/data.yaml')
                sudo('python ./src/manage.py dumpdata auth.user --settings=settings.settings --indent 2 --format yaml > ./data/data.yaml')

            with cd('/www/your.domain.com/'):
                get('./data/data.yaml', backup_path)
                get('./public', backup_path)
