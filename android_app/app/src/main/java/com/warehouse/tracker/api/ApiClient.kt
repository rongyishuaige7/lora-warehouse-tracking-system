package com.warehouse.tracker.api

import com.warehouse.tracker.BuildConfig
import com.warehouse.tracker.util.UrlUtils
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * API客户端单例
 */
object ApiClient {

    /** 默认服务器地址，可在 APP 内「服务器」设置中修改 */
    private const val DEFAULT_BASE_URL = "http://10.0.2.2:5000/"

    @Volatile
    private var currentBaseUrl: String = DEFAULT_BASE_URL

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY else HttpLoggingInterceptor.Level.NONE
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(45, TimeUnit.SECONDS)
        .readTimeout(45, TimeUnit.SECONDS)
        .writeTimeout(45, TimeUnit.SECONDS)
        .build()

    @Volatile
    private var retrofit: Retrofit = createRetrofit(DEFAULT_BASE_URL)

    @Volatile
    private var _apiService: ApiService = retrofit.create(ApiService::class.java)

    val apiService: ApiService
        get() = _apiService

    private fun createRetrofit(baseUrl: String): Retrofit {
        require(UrlUtils.isValidBaseUrl(baseUrl)) {
            "Only HTTPS or trusted local/private HTTP server URLs are allowed"
        }
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        currentBaseUrl = normalized
        return Retrofit.Builder()
            .baseUrl(normalized)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }

    fun baseUrl(): String = currentBaseUrl

    fun defaultBaseUrl(): String = DEFAULT_BASE_URL

    /**
     * 更新服务器地址
     */
    fun updateBaseUrl(newBaseUrl: String) {
        synchronized(this) {
            retrofit = createRetrofit(newBaseUrl)
            _apiService = retrofit.create(ApiService::class.java)
        }
    }
}
