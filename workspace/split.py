import re
cword = '\cite{}'
innards = re.compile(r'cite[{](.*?)[}]').search(cword).groups()[0].strip()
print innards
entries = innards.strip().split(",")
print entries
