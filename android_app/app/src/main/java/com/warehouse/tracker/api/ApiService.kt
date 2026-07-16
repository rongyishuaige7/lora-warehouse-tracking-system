package com.warehouse.tracker.api

import com.warehouse.tracker.model.Device
import com.warehouse.tracker.model.LocateRequest
import com.warehouse.tracker.model.LocateResponse
import retrofit2.Response
import retrofit2.http.*

/**
 * API服务接口
 */
interface ApiService {

    /**
     * 获取所有设备
     */
    @GET("api/devices")
    suspend fun getDevices(): Response<List<Device>>

    /**
     * 获取单个设备
     */
    @GET("api/devices/{id}")
    suspend fun getDevice(@Path("id") id: String): Response<Device>

    /**
     * 搜索设备
     */
    @GET("api/search")
    suspend fun searchDevices(@Query("q") query: String): Response<List<Device>>

    /**
     * 获取区域统计
     */
    @GET("api/regions")
    suspend fun getRegions(): Response<Map<String, Int>>

    /**
     * 定位设备并触发语音
     */
    @POST("api/locate")
    suspend fun locate(@Body request: LocateRequest): Response<LocateResponse>

    /**
     * 健康检查
     */
    @GET("api/health")
    suspend fun health(): Response<Map<String, String>>
}
