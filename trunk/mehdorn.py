import httplib
conn = httplib.HTTPConnection("www.bahn.de")
conn.request("GET", "/p/view/index.shtml")
r1 = conn.getresponse()
print r1.status, r1.reason



data1 = r1.read()

print data1

conn.close()
