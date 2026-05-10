# Public web bang Cloudflare Tunnel

Muc tieu:

```text
https://capcut.hieupro.io.vn
  -> Cloudflare Tunnel
  -> http://127.0.0.1:8080
  -> Auto Translate Video
```

File duy nhat can chay tren may nay:

```text
start_public_web.bat
```

## Cach chay web

1. Bam `start_public_web.bat`.
2. Chon `2. Chay an`.
3. Kiem tra local:

```text
http://127.0.0.1:8080/
```

Neu local vao duoc nhung domain khong vao duoc thi loi nam o Cloudflare Tunnel/Public Hostname, khong phai web app.

## Cau hinh dung tren Cloudflare

Vao Cloudflare Zero Trust:

```text
Networks -> Tunnels -> chon tunnel dang chay -> Public Hostnames
```

Them hoac sua hostname:

```text
Subdomain: capcut
Domain: hieupro.io.vn
Type: HTTP
URL: 127.0.0.1:8080
```

Ket qua dung:

```text
capcut.hieupro.io.vn -> HTTP -> http://127.0.0.1:8080
```

Neu Cloudflare yeu cau URL day du, nhap:

```text
http://127.0.0.1:8080
```

## Cach truy cap

Chi truy cap bang link nay:

```text
https://capcut.hieupro.io.vn/
```

Khong truy cap:

```text
http://capcut.hieupro.io.vn:8080/
```

Ly do: port `8080` chi la port noi bo tren may chay app. Khi dung Cloudflare Tunnel, ben ngoai di qua HTTPS port `443` cua Cloudflare, khong di truc tiep vao port `8080` cua may.

## Loi 502 Bad Gateway

Neu domain tra `502 Bad Gateway` tu Cloudflare, thuong la do Public Hostname tro sai service URL.

Can kiem tra:

- Web local phai vao duoc: `http://127.0.0.1:8080/`.
- Tunnel service phai dang Running tren Windows.
- Public Hostname phai la `HTTP -> 127.0.0.1:8080`.
- Neu `cloudflared` chay bang Docker, service URL phai doi thanh `http://host.docker.internal:8080`.
- Khong tao DNS A record tro ve IP public khi dung Tunnel; de Cloudflare Tunnel tu tao CNAME ve `cfargotunnel.com`.

## Lenh nhanh

Kiem tra web local:

```powershell
curl.exe -L http://127.0.0.1:8080/
```

Kiem tra port app:

```powershell
netstat -ano | findstr /C:":8080" | findstr /C:"LISTENING"
```

Kiem tra service tunnel:

```powershell
Get-Service cloudflared
```

