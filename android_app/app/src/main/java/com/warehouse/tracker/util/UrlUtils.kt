package com.warehouse.tracker.util

import java.net.URI

object UrlUtils {
    /**
     * HTTPS may use a normal host. Plain HTTP is restricted to loopback,
     * Android's emulator host, or RFC1918 addresses because this prototype
     * has no API authentication or TLS termination of its own.
     */
    @JvmStatic
    fun isValidBaseUrl(url: String): Boolean {
        if (url.isBlank()) return false
        return try {
            val uri = URI(url.trim())
            val scheme = uri.scheme?.lowercase() ?: return false
            val host = uri.host?.lowercase() ?: return false
            if (uri.userInfo != null || uri.query != null || uri.fragment != null) return false
            if (uri.port < -1 || uri.port > 65535) return false
            when (scheme) {
                "https" -> true
                "http" -> isPrivateOrLoopback(host)
                else -> false
            }
        } catch (_: Exception) {
            false
        }
    }

    private fun isPrivateOrLoopback(host: String): Boolean {
        if (host == "localhost" || host == "::1" || host == "10.0.2.2") return true
        val octets = host.split(".").mapNotNull { it.toIntOrNull() }
        if (octets.size != 4 || octets.any { it !in 0..255 }) return false
        return octets[0] == 127 ||
                octets[0] == 10 ||
                (octets[0] == 172 && octets[1] in 16..31) ||
                (octets[0] == 192 && octets[1] == 168)
    }
}
