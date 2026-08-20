package com.zimstudy.app.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun FeatureScreen(route: String, onBack: () -> Unit) {
    val title = when (route) { "teacher" -> "AI Teacher"; "quiz" -> "Practice Quiz"; "examiner" -> "Formal Examiner"; "progress" -> "Progress"; "library" -> "Document Library"; "report" -> "Weekly Report"; else -> "Study System" }
    val description = when (route) { "teacher" -> "Explain concepts, simplify topics, check understanding, and recommend what to study next."; "quiz" -> "Practice by subject, topic, and difficulty, then identify weak topics."; "examiner" -> "Take formal assessments separately from practice, with marks, feedback, and weak areas."; "progress" -> "Track study time, sessions, practice, assessments, mastery, and readiness estimates."; "library" -> "Keep notes, textbooks, past papers, and transcripts together."; else -> "Review real study time, sessions, results, strong areas, weak areas, and recommendations." }
    var question by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        TextButton(onClick = onBack) { Text("← Dashboard") }
        Text(title, style = MaterialTheme.typography.headlineSmall)
        Spacer(Modifier.height(8.dp))
        Text(description, style = MaterialTheme.typography.bodyLarge)
        Spacer(Modifier.height(20.dp))
        Card(Modifier.fillMaxWidth()) { Column(Modifier.padding(16.dp)) { Text("CONNECTED STUDY MODULE", style = MaterialTheme.typography.labelMedium); Text("This module uses your saved academic activity and works with your subjects and timer sessions.") } }
        if (route == "teacher") { Spacer(Modifier.height(16.dp)); OutlinedTextField(value = question, onValueChange = { question = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Ask your Teacher") }); Button(onClick = { if (question.isBlank()) question = "Type a question first" }, modifier = Modifier.padding(top = 10.dp)) { Text("Ask") } }
        else { Spacer(Modifier.height(20.dp)); Text("Next action", style = MaterialTheme.typography.titleMedium); Text("Choose a subject and topic, complete the activity, then return to Progress to review the result.", modifier = Modifier.padding(top = 8.dp)) }
    }
}
