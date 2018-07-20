# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "ubuntu/xenial64"

  config.vm.provider "virtualbox" do |v|
    # v.gui = true should be commented out by default, because headless connection is way faster.
    # If you still wanna use the Ortho4XP GUI, please uncomment the line below `v.gui = true` by removing the #
    # Please remember to uncomment the ubuntu-desktop installation command in provision_script.sh as well

    # v.gui = true
    v.customize ["modifyvm", :id, "--memory", "2048"]
  end

  config.vm.provision "shell", inline: <<-SCRIPT
echo "Updating ubuntu password"
echo "ubuntu:ubuntu" | chpasswd
SCRIPT

  config.vm.provision :shell, path: "provision_script.sh"
end
