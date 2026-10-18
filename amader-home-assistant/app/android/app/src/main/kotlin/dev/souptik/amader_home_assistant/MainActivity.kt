package dev.souptik.amader_home_assistant

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val notificationManager = getSystemService(NotificationManager::class.java)
            val alarmAudioAttributes = AudioAttributes.Builder()
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .setUsage(AudioAttributes.USAGE_ALARM)
                .build()
            val channel = NotificationChannel(
                "doorbell_critical_alerts",
                "Critical doorbell alerts",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = "Immediate alerts when someone rings the doorbell"
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 500, 250, 500)
                lockscreenVisibility = Notification.VISIBILITY_PUBLIC
                setSound(
                    RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM),
                    alarmAudioAttributes,
                )
                if (notificationManager.isNotificationPolicyAccessGranted) {
                    setBypassDnd(true)
                }
            }
            notificationManager.createNotificationChannel(channel)
        }
    }
}
