import subprocess
import time
from mininet.log import setLogLevel, info
import os

def load_pids():
    pids = {}
    with open('/tmp/mininet_pids.env') as f:
        for line in f:
            name, pid = line.strip().split('=')
            pids[name] = pid
    return pids

def run_in_host(pid, cmd):
    """Esegue un comando dentro il namespace dell'host tramite mnexec"""
    return subprocess.run(f"mnexec -a {pid} {cmd}", shell=True, capture_output=True, text=True)

def main():
    pids = load_pids()
    print(f"[*] Agganciato alla topologia attiva: {pids}")
    
    # 1. Avvia iperf3 server su h2 e h3
    run_in_host(pids['h2'], 'iperf3 -s -p 5201 -D')
    run_in_host(pids['h3'], 'iperf3 -s -p 5202 -D')

    # 2. Avvia iperf3 client su h1
    subprocess.Popen(f"mnexec -a {pids['h1']} iperf3 -c 10.0.2.2 -u -b 12M -p 5202 -t 10 > results/h3_iperf.txt", shell=True)
    run_in_host(pids['h1'], 'iperf3 -c 10.0.2.1 -u -b 2M -p 5201 -t 10 > results/h2_iperf.txt')

    # 3. Lancia lo spoofing su m1
    run_in_host(pids['m1'], 'python3 test_arp.py > results/arp_attack.txt')
    
    # 4. Verifica il blocco di m1
    res = run_in_host(pids['m1'], 'ping -c 2 10.0.1.1')
    with open('results/ping_after_attack.txt', 'w') as f:
        f.write(res.stdout)
    
    print("Collecting Queue stats from OVS...")

    stats = os.popen('ovs-ofctl queue-stats s1 3 -O OpenFlow13').read()
    with open('./results/ovs_queue_stats.txt', 'w') as f:
        f.write(stats)

    print("Test completed.")

if __name__ == '__main__':
    setLogLevel('info')
    main()
