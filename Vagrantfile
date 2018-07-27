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

  config.vm.synced_folder "./", "/vagrant", owner: "vagrant", group: "vagrant", mount_options: ["dmode=775,fmode=775"]

  ###########################################
  # Enable the synced_folder based on your OS.

  # 1. Enable the line below and update the path to point your X-Plane 11 path in Mac. This is to allow selecting overlay folder.
  # config.vm.synced_folder "/Users/yamin/Desktop/X-Plane 11", "/vagrant/xplane_11", owner: "vagrant", group: "vagrant", mount_options: ["dmode=775,fmode=775"]

  # 2. Enable the line below and update the path to point your X-Plane 11 path in Windows. This is to allow selecting overlay folder.
  # config.vm.synced_folder "D:/X-Plane 11", "/vagrant/xplane_11", owner: "vagrant", group: "vagrant", mount_options: ["dmode=775,fmode=775"]

  ###########################################

  config.vm.provision "shell", inline: <<-SCRIPT
echo "Updating ubuntu password"
echo "ubuntu:ubuntu" | chpasswd
SCRIPT

  config.vm.provision :shell, path: "Ortho4XP_provision_script.sh"
end
