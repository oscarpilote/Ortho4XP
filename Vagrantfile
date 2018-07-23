# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/xenial64"

  config.vm.provider "virtualbox" do |v|
    # comment v.gui = true to get headless Ubuntu which is way faster.

    v.gui = true
    v.customize ["modifyvm", :id, "--memory", "2048"]
    v.customize ["modifyvm", :id, "--vram", "128"]
    v.customize ["modifyvm", :id, "--accelerate3d", "on"]
    v.customize ["storageattach", :id,
        "--storagectl", "IDE",
        "--port", "0",
        "--device", "1",
        "--type", "dvddrive",
        "--medium", "emptydrive"]
  end

  config.vm.provision "shell", inline: <<-SCRIPT
echo "Updating ubuntu password"
echo "ubuntu:ubuntu" | chpasswd
SCRIPT

  config.vm.provision :shell, path: "Ortho4XP_provision_script.sh"
end
