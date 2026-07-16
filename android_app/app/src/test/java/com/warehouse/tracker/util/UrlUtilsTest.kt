package com.warehouse.tracker.util

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UrlUtilsTest {

    @Test
    fun validBaseUrl_http() {
        assertTrue(UrlUtils.isValidBaseUrl("http://192.168.50.10:5000"))
        assertTrue(UrlUtils.isValidBaseUrl("http://10.0.2.2:5000"))
        assertTrue(UrlUtils.isValidBaseUrl("http://172.16.1.10:5000"))
        assertTrue(UrlUtils.isValidBaseUrl("http://localhost:5000/"))
    }

    @Test
    fun validBaseUrl_https() {
        assertTrue(UrlUtils.isValidBaseUrl("https://api.example.com"))
    }

    @Test
    fun invalidBaseUrl_blank() {
        assertFalse(UrlUtils.isValidBaseUrl(""))
        assertFalse(UrlUtils.isValidBaseUrl("   "))
    }

    @Test
    fun invalidBaseUrl_otherSchemes() {
        assertFalse(UrlUtils.isValidBaseUrl("ftp://host"))
        assertFalse(UrlUtils.isValidBaseUrl("file:///path"))
    }

    @Test
    fun invalidBaseUrl_publicCleartextOrAmbiguous() {
        assertFalse(UrlUtils.isValidBaseUrl("http://example.com"))
        assertFalse(UrlUtils.isValidBaseUrl("http://8.8.8.8:5000"))
        assertFalse(UrlUtils.isValidBaseUrl("http://user:pass@192.168.50.10"))
        assertFalse(UrlUtils.isValidBaseUrl("https:///missing-host"))
    }
}
