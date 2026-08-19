package com.zimstudy.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

@Composable
fun TimerScreen(
    subject: String,
    topic: String,
    onSessionComplete: (minutesStudied: Int) -> Unit,
    onCancel: () -> Unit
) {
    var secondsElapsed by remember { mutableStateOf(0) }
    var running by remember { mutableStateOf(true) }

    LaunchedEffect(running) {
        while (running) {
            delay(1000)
            secondsElapsed++
        }
    }

    val minutes = secondsElapsed / 60
    val seconds = secondsElapsed % 60

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(subject, style = MaterialTheme.typography.titleMedium)
        Text(topic, style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.height(24.dp))
        Text(
            String.format("%02d:%02d", minutes, seconds),
            style = MaterialTheme.typography.displayLarge,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(32.dp))

        Row {
            OutlinedButton(onClick = { running = !running }) {
                Text(if (running) "Pause" else "Resume")
            }
            Spacer(Modifier.width(16.dp))
            Button(onClick = {
                running = false
                onSessionComplete(minutes.coerceAtLeast(1))
            }) {
                Text("Complete Session")
            }
        }

        Spacer(Modifier.height(16.dp))
        TextButton(onClick = onCancel) { Text("Cancel") }
    }
}
