#!/bin/bash

WEBSITE_PATH=/www/your.domain.com


set -e
set -o pipefail


apt-get update

sudo apt-get install -y python-dev python-software-properties

add-apt-repository -y ppa:nginx/stable

apt-get -y upgrade


# ~ install locales and timezone ~
echo "Europe/Kiev" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata

apt-get -y install locales
cat > /etc/default/locale <<END
LANGUAGE=en_US:en
LANG="en_US.UTF-8"
END

cat > /etc/locale.gen << EOF
en_US.UTF-8 UTF-8
EOF

locale-gen


# General utilities, applications, tools
apt-get -y install curl wget sudo htop mc ntp

# SSH configuration
sed -i 's|^[#]*\s*\(PermitRootLogin\) .*$|\1 no|;' /etc/ssh/sshd_config
service ssh restart

# Add new sudo user and grant it with SSH access
groupadd admins

useradd -g admins -s /bin/bash --create-home -- user_name
passwd user_name <<END
user_password
user_password
END

sudo adduser user_name sudo


# ~ install python and its libraries ~
apt-get install -y libpcre3-dev build-essential libssl-dev
apt-get install -y python2.7-dev python-pip

apt-get install -y uwsgi uwsgi-plugin-python


# ~ install nginx ~
apt-get install -y nginx

rm -r /etc/nginx/sites-enabled/default
rm -r /etc/nginx/sites-available/default

ln -s ${WEBSITE_PATH}/conf/nginx /etc/nginx/sites-enabled/nginx

chmod -R 0755 ${WEBSITE_PATH}/public

chown -R www-data:www-data ${WEBSITE_PATH}/public/media
chgrp -R www-data ${WEBSITE_PATH}/public/media
chmod -R g+w ${WEBSITE_PATH}/public/media

service nginx reload
service nginx restart


# ~ install redis ~
apt-get install -y redis-server

sed -i 's|^[#]* \(maxmemory\) <.*$|\1 500mb|;s|^[#]* \(maxmemory-policy .*\)$|\1|;' /etc/redis/redis.conf

echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf
sysctl vm.overcommit_memory=1

ln -s /var/log/redis ${WEBSITE_PATH}/sys/logs/redis
ln -s /etc/init.d/redis-server ${WEBSITE_PATH}/bin/redis-server

service redis-server restart


# ~ install postgresql ~
sudo apt-get install -y postgresql postgresql-contrib libpq-dev

sed -i "s|^#\(listen_addresses\) = '.*'|\1 = 'localhost'|" /etc/postgresql/9.4/main/postgresql.conf

# !! TODO: check where the logs should be created...
# ln -s /var/log/postgresql ${WEBSITE_PATH}/sys/logs/postgresql

service postgresql restart

su postgres -c "
psql template1 <<END
CREATE USER django_db_user;
ALTER ROLE django_db_user WITH ENCRYPTED PASSWORD 'SomeSecurePasswordHere';
\q
END
createdb -O django_db_user django_db
exit
psql template1 <<END
GRANT ALL PRIVILEGES ON DATABASE django_db TO django_db_user;
\q
END
"


# ~ install image libraries ~
apt-get install -y libjpeg-dev libjpeg8-dev libfreetype6-dev zlib1g-dev libpng12-dev


# ~ install virtual environment for python ~
pip install virtualenv

# initialize virtual environment with no site packages
virtualenv ${WEBSITE_PATH}/sys/.venv --no-site-packages

# activate virtual environment to install all requirements in isolation
source ${WEBSITE_PATH}/sys/.venv/bin/activate

# install all requirements
pip install -r ${WEBSITE_PATH}/src/requirements.txt

python ${WEBSITE_PATH}/src/manage.py collectstatic --noinput --settings=settings.live

# make database migration of the project
python ${WEBSITE_PATH}/src/manage.py migrate --settings=settings.live
python ${WEBSITE_PATH}/src/manage.py loaddata ${WEBSITE_PATH}/data/data.yaml --settings=settings.live


# ~ install supervisor ~
apt-get install -y supervisor

ln -s ${WEBSITE_PATH}/conf/supervisor_uwsgi.conf /etc/supervisor/conf.d/supervisor_uwsgi.conf

# unlink /var/run/supervisor.pid

# service supervisor start

service supervisor restart

# ~ install apache utils ~

apt-get install -y apache2-utils
htpasswd -cb ${WEBSITE_PATH}/conf/.htpasswd 'user_name' 'user_password'

service nginx reload


# ~ install ufw ~

apt-get install -y ufw

ufw default deny
ufw logging on
ufw allow 22
ufw allow 80
ufw allow 443
ufw limit ssh/tcp

yes | ufw enable
