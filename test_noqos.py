from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch, Node
from mininet.link import TCLink
from mininet.log import setLogLevel, info
import os
import time

class LinuxRouter(Node):
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl net.ipv4.ip_forward=1')
    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

def run_no_qos_test():
    os.makedirs('results', exist_ok=True)

    # Usa link=TCLink per abilitare il bandwidth limiting sui link
    net = Mininet(controller=RemoteController, switch=OVSKernelSwitch, link=TCLink)
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6633)
    r1 = net.addHost('r1', cls=LinuxRouter, ip='10.0.1.254/24', mac='00:00:00:00:0a:01')
    s1 = net.addSwitch('s1', protocols='OpenFlow13')
    s2 = net.addSwitch('s2', protocols='OpenFlow13')
    
    h1 = net.addHost('h1', ip='10.0.1.1/24', mac='00:00:00:00:01:01', defaultRoute='via 10.0.1.254')
    m1 = net.addHost('m1', ip='10.0.1.2/24', mac='00:00:00:00:01:02', defaultRoute='via 10.0.1.254')
    h2 = net.addHost('h2', ip='10.0.2.1/24', mac='00:00:00:00:02:01', defaultRoute='via 10.0.2.254')
    h3 = net.addHost('h3', ip='10.0.2.2/24', mac='00:00:00:00:02:02', defaultRoute='via 10.0.2.254')

    net.addLink(h1, s1, port1=0, port2=1)
    net.addLink(m1, s1, port1=0, port2=2)
    # BOTTLE NECK: Link s1-r1 fissato a 10 Mbps tramite tc (senza code HTB di classe)
    net.addLink(s1, r1, port1=3, port2=0, bw=10, max_queue_size=10, params2={'ip': '10.0.1.254/24'})
    
    net.addLink(h2, s2, port1=0, port2=1)
    net.addLink(h3, s2, port1=0, port2=2)
    net.addLink(s2, r1, port1=3, port2=1, params2={'ip': '10.0.2.254/24'}, addr2='00:00:00:00:0b:01')

    net.build()
    c0.start()
    s1.start([c0])
    s2.start([c0])

    # Assicurati che non ci siano code OVS registrate
    os.system("ovs-vsctl clear port s1-eth3 qos 2>/dev/null")
    os.system("ovs-vsctl --all destroy qos 2>/dev/null")
    os.system("ovs-vsctl --all destroy queue 2>/dev/null")

    time.sleep(3)
    info('Verifica raggiungibilita con PingAll\n')
    net.pingAll()
    
    info('Avvio dei server iperf3 su h2 e h3...\n')
    h1.cmd('killall -9 iperf3 2>/dev/null')
    h2.cmd('killall -9 iperf3 2>/dev/null')
    h3.cmd('killall -9 iperf3 2>/dev/null')
    time.sleep(1)

    h2.cmd('iperf3 -s -p 5201 -D')
    h3.cmd('iperf3 -s -p 5202 -D')
    time.sleep(2)
    
    info('Generazione flussi simultanei SENZA QoS da h1 (Link limitato a 10 Mbps)...\n')
    # Flusso h3 (12M) in background
    h1.cmd('iperf3 -c 10.0.2.2 -u -b 12M -p 5202 -t 15 > results/noqos_h3_iperf.txt 2>&1 &')
    
    # Flusso h2 (2M) in foreground
    h1.cmd('iperf3 -c 10.0.2.1 -u -b 2M -p 5201 -t 15 > results/noqos_h2_iperf.txt 2>&1')

    time.sleep(2)
    
    h2.cmd('killall -9 iperf3 2>/dev/null')
    h3.cmd('killall -9 iperf3 2>/dev/null')
    
    net.stop()
    info('Test No-QoS Completato con successo.\n')

if __name__ == '__main__':
    setLogLevel('info')
    run_no_qos_test()