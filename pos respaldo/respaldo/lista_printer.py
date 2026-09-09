import win32print

printers = win32print.EnumPrinters(2)
for p in printers:
    print(p[2])
