package com.warehouse.tracker.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.warehouse.tracker.R
import com.warehouse.tracker.model.Device

/**
 * 设备列表 Adapter，使用 DiffUtil 差量刷新，避免搜索/筛选时全量 notifyDataSetChanged 卡顿。
 */
class DeviceAdapter(
    private val onLocateClick: (Device) -> Unit
) : ListAdapter<Device, DeviceAdapter.ViewHolder>(DeviceDiffCallback()) {

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val nameText: TextView = view.findViewById(R.id.deviceName)
        val idText: TextView = view.findViewById(R.id.deviceId)
        val regionText: TextView = view.findViewById(R.id.deviceRegion)
        val statusText: TextView = view.findViewById(R.id.deviceStatus)
        val locateBtn: Button = view.findViewById(R.id.locateBtn)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_device, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val device = getItem(position)

        holder.nameText.text = device.name.ifEmpty { device.deviceId }
        holder.idText.text = "编号: ${device.deviceId}"
        holder.regionText.text = "区域: ${device.region}"
        holder.statusText.text = "状态: ${device.status}"

        val statusColor = when (device.status) {
            "OK" -> android.graphics.Color.GREEN
            "MOVING" -> android.graphics.Color.YELLOW
            "REMOVED" -> android.graphics.Color.RED
            else -> android.graphics.Color.GRAY
        }
        holder.statusText.setTextColor(statusColor)

        holder.locateBtn.setOnClickListener {
            onLocateClick(device)
        }
    }

    /** 差量比较：按 deviceId 与关键展示字段，避免无关字段变化触发整表刷新 */
    private class DeviceDiffCallback : DiffUtil.ItemCallback<Device>() {
        override fun areItemsTheSame(old: Device, new: Device): Boolean =
            old.deviceId == new.deviceId

        override fun areContentsTheSame(old: Device, new: Device): Boolean =
            old == new
    }
}
