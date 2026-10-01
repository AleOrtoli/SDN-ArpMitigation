# Progetto SDN - Mininet, Ryu, QoS e Sicurezza ARP

## Struttura dei File
- `topo.py`: Script di avvio di Mininet. Definisce la topologia, il router Linux, e assegna gli indirizzi IP e MAC statici. Al termine dell'avvio della rete, configura le regole OVSDB per la QoS.
- `controller.py`: L'applicazione Ryu (OpenFlow 1.3). Gestisce L2 Learning, ARP spoofing protection, e imposta le code HTB in base agli indirizzi IP di destinazione (flusso UDP).
- `test_arp.py`: Script Python/Scapy che esegue l'attacco ARP Spoofing. Da eseguire su `m1`.

## Requisiti 
- Mininet
- Open vSwitch
- Docker (per eseguire il controller Ryu in modo semplice senza conflitti Python)
- iperf3
- python3-scapy

## Istruzioni per le Prove (Validazione del progetto)

### 1. Avviare il Controller SDN (Ryu)
Apri un terminale nella cartella del progetto (`~/sdn_project`) e avvia il controller:
```bash
ryu-manager /app/controller.py
```
*(Il log del monitoraggio QoS e degli attacchi verrà salvato sia a schermo che nel file `stats.log`)*

### 2. Avviare la Rete Mininet
Apri un SECONDO terminale e avvia la topologia:
```bash
sudo python3 topo.py
```
Attendi che appaia il prompt `mininet>`. Verifica la comunicazione di base:
```bash
mininet> pingall
```
*(Tutti i ping dovrebbero andare a buon fine, dimostrando il corretto L2 learning e routing)*

### 3. Congestione e QoS (Code)
Nel prompt di Mininet, apri due xterm (o esegui i comandi direttamente) per `h1`, `h2` e `h3`.
**Server in ricezione (LAN B):**
```bash
mininet> h2 iperf3 -s -p 5201 &
mininet> h3 iperf3 -s -p 5202 &
```
**Generazione traffico (LAN A) - Flusso Best Effort (12 Mbit/s):**
```bash
mininet> h1 iperf3 -c 10.0.2.2 -u -b 12M -p 5202 -t 15 &
```
**Generazione traffico (LAN A) - Flusso Prioritario (2 Mbit/s):**
```bash
mininet> h1 iperf3 -c 10.0.2.1 -u -b 2M -p 5201 -t 15 &
```
*(Nota come, grazie alle code HTB create via `ovs-vsctl` e alle regole `set_queue` iniettate dal controller per i flussi UDP, il traffico verso `10.0.2.1` (Coda 0, 3M min) manterrà i 2Mbit/s richiesti e basso jitter, mentre quello verso `10.0.2.2` subirà perdita di pacchetti a causa del limite a 10Mbit/s del bottleneck)*. 
Nel terminale del controller Ryu vedrai i byte accumularsi sulle rispettive code.

### 4. Test Sicurezza - Attacco ARP Spoofing
Dal prompt di mininet, esegui lo script malevolo dall'host `m1`:
```bash
mininet> m1 python3 test_arp.py
```
Guarda il terminale del controller Ryu! Apparirà:
`SECURITY ALERT: ARP Spoofing Detected! DPID: 1, Port: 2...`
Il controller non inoltrerà il pacchetto falsificato e installerà automaticamente una regola di DROP sullo switch 1 per l'attaccante (`m1`), impedendogli di interferire ulteriormente nella rete. Puoi testare provando a pingare da `m1` a `h1`, non funzionerà più!
