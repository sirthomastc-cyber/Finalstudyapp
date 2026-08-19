package com.zimstudy.app.ui
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.zimstudy.app.StudyViewModel
import java.util.concurrent.TimeUnit
@Composable
fun DashboardScreen(viewModel:StudyViewModel,onOpenSubjects:()->Unit,onStartTimer:(String,String)->Unit,onOpenFeature:(String)->Unit){
 val profile by viewModel.profile.collectAsState(); val subjects by viewModel.subjects.collectAsState(); val exams by viewModel.exams.collectAsState(); val nextExam=exams.minByOrNull{it.examDateMillis}; val days=nextExam?.let{TimeUnit.MILLISECONDS.toDays((it.examDateMillis-System.currentTimeMillis()).coerceAtLeast(0))}
 Column(Modifier.fillMaxSize().padding(20.dp)){ Text("Welcome back, ${profile?.name ?: "Student"}",style=MaterialTheme.typography.headlineSmall,fontWeight=FontWeight.Bold); Spacer(Modifier.height(12.dp)); Card(Modifier.fillMaxWidth()){Column(Modifier.padding(16.dp)){Text("NEXT EXAM",style=MaterialTheme.typography.labelMedium);Text(if(nextExam==null)"No exam dates added yet." else "${nextExam.subjectName} — Paper ${nextExam.paperNumber}",style=MaterialTheme.typography.titleMedium);if(days!=null)Text("$days days remaining")}}
 Spacer(Modifier.height(16.dp)); Row(Modifier.fillMaxWidth(),Arrangement.SpaceBetween){Text("Your Subjects",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold);TextButton(onOpenSubjects){Text("Manage")}}
 if(subjects.isEmpty())Text("No subjects yet. Tap Manage to add some.") else LazyColumn(Modifier.weight(1f)){items(subjects){subject->Card(Modifier.fillMaxWidth().padding(vertical=5.dp)){Row(Modifier.fillMaxWidth().padding(14.dp),Arrangement.SpaceBetween){Column(Modifier.weight(1f)){Text(subject.name);Text("Target: ${subject.targetGrade}",style=MaterialTheme.typography.bodySmall)};Button({onStartTimer(subject.name,"Focused session")}){Text("Start")}}}}}
 Text("Study system",style=MaterialTheme.typography.titleMedium,fontWeight=FontWeight.Bold); listOf("AI Teacher" to "teacher","Practice Quiz" to "quiz","Formal Examiner" to "examiner","Progress" to "progress","Library" to "library","Weekly Report" to "report").chunked(2).forEach{pair->Row(Modifier.fillMaxWidth(),Arrangement.spacedBy(8.dp)){pair.forEach{(label,route)->Button({onOpenFeature(route)},Modifier.weight(1f)){Text(label)}}}}
 }}
