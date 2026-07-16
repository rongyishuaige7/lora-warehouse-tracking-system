package com.warehouse.tracker.model

import com.google.gson.annotations.SerializedName

/**
 * 设备数据模型
 */
data class Device(
    @SerializedName("device_id")
    val deviceId: String,

    @SerializedName("name")
    val name: String = "",

    @SerializedName("region")
    val region: String = "",

    @SerializedName("status")
    val status: String = "OK",

    @SerializedName("temperature")
    val temperature: Double? = null,

    @SerializedName("humidity")
    val humidity: Double? = null,

    @SerializedName("battery")
    val battery: Double? = null,

    @SerializedName("last_update")
    val lastUpdate: Long = 0
)

/**
 * 定位请求
 */
data class LocateRequest(
    @SerializedName("device_id")
    val deviceId: String
)

/**
 * 定位响应
 */
data class LocateResponse(
    @SerializedName("region")
    val region: String,

    @SerializedName("device_id")
    val deviceId: String,

    @SerializedName("message")
    val message: String = "",

    @SerializedName("gateway_command_sent")
    val gatewayCommandSent: Boolean = true,

    @SerializedName("gateway_error")
    val gatewayError: String? = null,

    @SerializedName("tag_delivery_confirmed")
    val tagDeliveryConfirmed: Boolean = false,

    @SerializedName("last_report_age_seconds")
    val lastReportAgeSeconds: Long? = null
)

/**
 * 区域统计
 */
data class RegionStats(
    val A: Int = 0,
    val B: Int = 0
)
