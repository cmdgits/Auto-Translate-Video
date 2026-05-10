# Public web bang mot file BAT

File duy nhat can chay:

```text
start_public_web.bat
```

## Cach dung

- Lan dau: bam chuot phai `start_public_web.bat` -> **Run as administrator**.
- Chon `1` de chay co UI/log, hoac chon `2` de chay an.
- Tu lan sau: double-click `start_public_web.bat`, chon kieu chay ban muon.

File nay tu:

- Chay web tren `0.0.0.0:80`.
- Mo Windows Firewall port `80` neu dang chay bang Administrator.
- Khong bat dang nhap khi truy cap web.
- Neu chay an, log nam trong `public_web_hidden.log` va `public_web_hidden_error.log`.

## Tro domain ve server

Voi bat ky ten mien nao, tao DNS A record ve IP public cua server/mang nha ban:

```text
Type: A
Name: @ hoac subdomain
Value: IP public cua server
```

Router/modem can port-forward:

```text
External TCP 80 -> IP LAN may chay app TCP 80
```

Ten mien nao tro ve dung IP public do deu vao cung web.

## Dung server an / dong firewall

- Chon `3` trong menu de dung server an.
- Chon `4` trong menu de dong firewall port `80`.

Hoac chay bang Administrator:


```text
start_public_web.bat close
```

## Luu y

- Neu port `80` bi phan mem khac chiem, hay tat IIS/Nginx/Apache hoac doi cau hinh port.
- Neu nha mang dung CGNAT/khong co IP public that, port-forward se khong vao duoc.
