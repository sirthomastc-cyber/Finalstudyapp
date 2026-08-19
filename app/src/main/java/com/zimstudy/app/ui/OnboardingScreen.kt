package com.zimstudy.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@Composable
fun OnboardingScreen(
    onComplete: (name: String, school: String, grade: String, examBoard: String, examYear: String) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var school by remember { mutableStateOf("") }
    var grade by remember { mutableStateOf("") }
    var examBoard by remember { mutableStateOf("ZIMSEC") }
    var examYear by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            "LET'S BUILD YOUR STUDY SYSTEM",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )
        Text(
            "A few details to set up your academic profile.",
            style = MaterialTheme.typography.bodyMedium
        )

        OutlinedTextField(
            value = name,
            onValueChange = { name = it },
            label = { Text("Your name") },
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = school,
            onValueChange = { school = it },
            label = { Text("School (optional)") },
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = grade,
            onValueChange = { grade = it },
            label = { Text("Grade / Form") },
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = examBoard,
            onValueChange = { examBoard = it },
            label = { Text("Examination board") },
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = examYear,
            onValueChange = { examYear = it },
            label = { Text("Examination year") },
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(8.dp))

        Button(
            onClick = { onComplete(name.ifBlank { "Student" }, school, grade, examBoard, examYear) },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Start")
        }
    }
}
