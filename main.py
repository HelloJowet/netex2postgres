from shared import load_xml
from Process import Process

root = load_xml('../norway_netex/_stops.xml')
netex_publication = Process().main(root)
print(netex_publication['Parking'])