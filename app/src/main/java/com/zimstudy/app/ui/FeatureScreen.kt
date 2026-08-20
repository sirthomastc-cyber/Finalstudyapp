package com.zimstudy.app.ui
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
@Composable
fun FeatureScreen(route:String,onBack:()->Unit){Column(Modifier.fillMaxSize().padding(20.dp)){TextButton(onClick=onBack){Text("Back")};Spacer(Modifier.height(16.dp));Text(route.replaceFirstChar{it.uppercase()}+" module",style=MaterialTheme.typography.headlineSmall);Spacer(Modifier.height(8.dp));Text("Academic tools for learning, practice, formal assessment, documents, progress and weekly review.")}}
