# -*- mode: ruby -*-
# vi: set ft=ruby :

# Ubuntu Vagrant boxes can be found here
#   https://vagrantcloud.com/ubuntu

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
    config.vm.box = "ubuntu/vivid32"
    config.vm.network "forwarded_port", guest: 80, host: 8080
    config.vm.network "forwarded_port", guest: 443, host: 8443

    config.vm.provider "virtualbox" do |v|
        v.memory = 2048
        v.cpus = 2
    end
end