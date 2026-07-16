package com.warehouse.tracker

import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.google.android.material.card.MaterialCardView
import com.warehouse.tracker.adapter.DeviceAdapter
import com.warehouse.tracker.api.ApiClient
import com.warehouse.tracker.model.Device
import com.warehouse.tracker.util.UrlUtils
import com.warehouse.tracker.model.LocateRequest
import kotlinx.coroutines.launch

/**
 * 主Activity
 */
class MainActivity : AppCompatActivity() {

    private lateinit var regionCardA: MaterialCardView
    private lateinit var regionCardB: MaterialCardView
    private lateinit var textCountA: TextView
    private lateinit var textCountB: TextView
    private lateinit var settingsBtn: TextView
    private lateinit var refreshBtn: TextView
    private lateinit var searchEditText: EditText
    private lateinit var deviceRecyclerView: RecyclerView
    private lateinit var loadingProgress: ProgressBar
    private lateinit var emptyView: TextView

    private lateinit var deviceAdapter: DeviceAdapter
    private var allDevices: List<Device> = emptyList()
    private var selectedRegion: String? = null

    private val prefs by lazy { getSharedPreferences("warehouse_tracker", MODE_PRIVATE) }
    private val prefBaseUrlKey = "base_url"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        applySavedBaseUrl()
        setupRecyclerView()
        setupSearch()
        setupActions()
        loadData()
    }

    private fun initViews() {
        regionCardA = findViewById(R.id.regionCardA)
        regionCardB = findViewById(R.id.regionCardB)
        textCountA = findViewById(R.id.textCountA)
        textCountB = findViewById(R.id.textCountB)
        settingsBtn = findViewById(R.id.settingsBtn)
        refreshBtn = findViewById(R.id.refreshBtn)
        searchEditText = findViewById(R.id.searchEditText)
        deviceRecyclerView = findViewById(R.id.deviceRecyclerView)
        loadingProgress = findViewById(R.id.loadingProgress)
        emptyView = findViewById(R.id.emptyView)
    }

    private fun setupRecyclerView() {
        deviceAdapter = DeviceAdapter { device -> locateDevice(device) }

        deviceRecyclerView.layoutManager = LinearLayoutManager(this)
        deviceRecyclerView.adapter = deviceAdapter
    }

    private fun setupSearch() {
        searchEditText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                applyFilters()
            }
        })
    }

    private fun setupActions() {
        refreshBtn.setOnClickListener { loadData() }
        settingsBtn.setOnClickListener { showServerSettingsDialog() }

        regionCardA.setOnClickListener { toggleRegionFilter("A") }
        regionCardB.setOnClickListener { toggleRegionFilter("B") }
        updateRegionCardUi()
    }

    private fun loadData() {
        loadingProgress.visibility = View.VISIBLE

        lifecycleScope.launch {
            try {
                // 区域统计失败也不影响设备列表；分别处理错误更友好
                try {
                    loadRegions()
                } catch (e: Exception) {
                    // 忽略，仍继续加载设备
                }

                try {
                    loadDevices()
                } catch (e: Exception) {
                    Toast.makeText(
                        this@MainActivity,
                        "${getString(R.string.load_failed)}: ${e.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            } catch (e: Exception) {
                Toast.makeText(
                    this@MainActivity,
                    "${getString(R.string.load_failed)}: ${e.message}",
                    Toast.LENGTH_SHORT
                ).show()
            } finally {
                loadingProgress.visibility = View.GONE
            }
        }
    }

    private suspend fun loadRegions() {
        val response = ApiClient.apiService.getRegions()
        if (response.isSuccessful) {
            val regions = response.body() ?: emptyMap()
            textCountA.text = getString(R.string.device_count, regions["A"] ?: 0)
            textCountB.text = getString(R.string.device_count, regions["B"] ?: 0)
        }
    }

    private suspend fun loadDevices() {
        val response = ApiClient.apiService.getDevices()
        if (response.isSuccessful) {
            allDevices = response.body() ?: emptyList()
            applyFilters()
        } else {
            val msg = parseErrorMessage(response.errorBody()?.string())
            throw Exception(msg.ifBlank { "HTTP ${response.code()}" })
        }
    }

    private fun applyFilters() {
        val keyword = searchEditText.text?.toString()?.trim().orEmpty()

        var filtered = allDevices
        val region = selectedRegion
        if (!region.isNullOrBlank()) {
            filtered = filtered.filter { it.region.equals(region, ignoreCase = true) }
        }

        if (keyword.isNotEmpty()) {
            filtered = filtered.filter {
                it.deviceId.contains(keyword, ignoreCase = true) ||
                        it.name.contains(keyword, ignoreCase = true)
            }
        }

        deviceAdapter.submitList(filtered)
        updateEmptyState(filtered.isEmpty())
    }

    private fun updateEmptyState(isEmpty: Boolean) {
        emptyView.visibility = if (isEmpty) View.VISIBLE else View.GONE
        deviceRecyclerView.visibility = if (isEmpty) View.GONE else View.VISIBLE
    }

    private fun locateDevice(device: Device) {
        lifecycleScope.launch {
            try {
                val response = ApiClient.apiService.locate(LocateRequest(device.deviceId))
                if (response.isSuccessful) {
                    val result = response.body()
                    val msg = result?.message ?: getString(R.string.locate_success)
                    Toast.makeText(this@MainActivity, msg, Toast.LENGTH_LONG).show()
                } else {
                    val errorBody = response.errorBody()?.string()
                    val serverMessage = parseErrorMessage(errorBody)
                    val msg = serverMessage.ifBlank { getString(R.string.locate_failed) }
                    Toast.makeText(this@MainActivity, msg, Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                Toast.makeText(
                    this@MainActivity,
                    "${getString(R.string.network_error)}: ${e.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
    }

    /** 从服务端 JSON 中解析 status=error 时的 message 字段 */
    private fun parseErrorMessage(errorBody: String?): String {
        if (errorBody.isNullOrBlank()) return ""
        return try {
            org.json.JSONObject(errorBody).optString("message", "").trim()
        } catch (_: Exception) {
            ""
        }
    }

    private fun toggleRegionFilter(region: String) {
        selectedRegion = if (selectedRegion == region) null else region
        updateRegionCardUi()
        applyFilters()

        val msg = selectedRegion?.let { getString(R.string.filter_region_on, it) }
            ?: getString(R.string.filter_region_off)
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }

    private fun updateRegionCardUi() {
        val selected = selectedRegion
        regionCardA.alpha = if (selected == null || selected == "A") 1.0f else 0.5f
        regionCardB.alpha = if (selected == null || selected == "B") 1.0f else 0.5f
    }

    private fun applySavedBaseUrl() {
        val saved = prefs.getString(prefBaseUrlKey, null)
        if (!saved.isNullOrBlank() && UrlUtils.isValidBaseUrl(saved)) {
            ApiClient.updateBaseUrl(saved)
        } else if (!saved.isNullOrBlank()) {
            prefs.edit().remove(prefBaseUrlKey).apply()
        }
    }

    private fun showServerSettingsDialog() {
        val input = EditText(this).apply {
            hint = getString(R.string.server_url_hint)
            setText(prefs.getString(prefBaseUrlKey, ApiClient.baseUrl()))
        }

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.server_settings))
            .setView(input)
            .setPositiveButton(getString(R.string.save)) { _, _ ->
                val url = input.text?.toString()?.trim().orEmpty()
                if (!UrlUtils.isValidBaseUrl(url)) {
                    Toast.makeText(this, getString(R.string.base_url_invalid), Toast.LENGTH_SHORT)
                        .show()
                    return@setPositiveButton
                }
                prefs.edit().putString(prefBaseUrlKey, url).apply()
                ApiClient.updateBaseUrl(url)
                Toast.makeText(this, getString(R.string.base_url_saved), Toast.LENGTH_SHORT).show()
                loadData()
            }
            .setNeutralButton(getString(R.string.reset)) { _, _ ->
                prefs.edit().remove(prefBaseUrlKey).apply()
                ApiClient.updateBaseUrl(ApiClient.defaultBaseUrl())
                Toast.makeText(this, getString(R.string.base_url_reset), Toast.LENGTH_SHORT).show()
                loadData()
            }
            .setNegativeButton(getString(R.string.cancel), null)
            .show()
    }

    override fun onResume() {
        super.onResume()
        loadData()
    }
}
