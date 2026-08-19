package com.zimstudy.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.zimstudy.app.StudyViewModel
import java.util.concurrent.TimeUnit

@Composable
fun DashboardScreen(
    viewModel: StudyViewModel,
    onOpenSubjects: () -> Unit,
    onStartTimer: (subject: String, topic: String) -> Unit
) {
    val profile by viewModel.profile.collectAsState()
    val subjects by viewModel.subjects.collectAsState()
    val exams by viewModel.exams.collectAsState()

    val nextExam = exams.minByOrNull { it.examDateMillis }
    val daysToExam = nextExam?.let {
        val diff = it.examDateMillis - System.currentTimeMillis()
        TimeUnit.MILLISECONDS.toDays(diff).coerceAtLeast(0)
    }

    Column(modifier = Modifier.fillMaxSize().padding(20.dp)) {
        Text(
            "Welcome back, ${profile?.name ?: "Student"}",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )
        Spacer(Modifier.height(12.dp))

        if (nextExam != null) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("NEXT EXAM", style = MaterialTheme.typography.labelMedium)
                    Text(
                        "${nextExam.subjectName} — Paper ${nextExam.paperNumber}",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text("$daysToExam days remaining", style = MaterialTheme.typography.bodyLarge)
                }
            }
        } else {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("No exam dates added yet.", style = MaterialTheme.typography.bodyMedium)
                }
            }
        }

        Spacer(Modifier.height(20.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("Your Subjects", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            TextButton(onClick = onOpenSubjects) { Text("Manage") }
        }

        if (subjects.isEmpty()) {
            Text("No subjects yet. Tap Manage to add some.", style = MaterialTheme.typography.bodyMedium)
        } else {
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(subjects) { subject ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 6.dp)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column {
                                Text(subject.name, style = MaterialTheme.typography.titleSmall)
                                Text("Target: ${subject.targetGrade}", style = MaterialTheme.typography.bodySmall)
                            }
                            Button(onClick = { onStartTimer(subject.name, "Focused session") }) {
                                Text("Start")
                            }
                        }
                    }
                }
            }
        }
    }
}
