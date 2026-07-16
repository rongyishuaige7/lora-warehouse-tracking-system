# Security policy

## Scope

This repository is an educational warehouse-tracking prototype, not a
production asset-security, access-control, or industrial positioning system.

## Network and radio boundary

The current design has no end-to-end authentication or encryption:

- tag-to-gateway LoRa messages are plaintext and have no replay protection;
- gateway `/control` accepts unauthenticated HTTP commands;
- gateway-to-Flask and Flask-to-gateway traffic is plaintext HTTP;
- Flask API has no user authentication or authorization;
- browser CORS is disabled by default, but CORS is not an authentication layer.

Use only on an isolated, trusted LAN and in a legally permitted radio test
environment. Do not port-forward the Flask or gateway ports, expose them to the
public internet, or use the prototype to protect valuable assets.

The Android app accepts HTTPS endpoints. Plain HTTP is restricted in app logic
to loopback, Android emulator host, and RFC1918 private addresses. This reduces
accidental public cleartext use; it does not make the LAN protocol secure.

## Credentials and private data

Local files `esp32_tag/config.h`, `esp32_gateway/config.h`, `server/config.json`,
`android_app/local.properties`, databases, build output, and logs do not belong
in version control. Never submit real Wi-Fi credentials, tokens, cookies,
private keys, personal paths, device identifiers, private IP inventories, or
location history in an issue.

## Reporting

Use GitHub private vulnerability reporting if enabled. Otherwise open a minimal,
redacted issue asking for a private follow-up channel. Do not include a working
exploit against someone else's network or radio equipment.

## Supported versions

Until a tagged release exists, only the latest `main` commit is maintained.
