package com.zimstudy.app
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.zimstudy.app.ui.*
class MainActivity : ComponentActivity() {
 private val viewModel: StudyViewModel by viewModels()
 override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContent { MaterialTheme { Surface(Modifier.fillMaxSize()) { val navController=rememberNavController(); val profile by viewModel.profile.collectAsState(); NavHost(navController, if(profile==null) "onboarding" else "dashboard") {
  composable("onboarding") { OnboardingScreen { name,school,grade,board,year -> viewModel.saveProfile(name,school,grade,board,year); navController.navigate("dashboard") { popUpTo("onboarding") { inclusive=true } } } }
  composable("dashboard") { DashboardScreen(viewModel,{navController.navigate("subjects")},{s,t->viewModel.startSession(s,t);navController.navigate("timer")},{navController.navigate(it)}) }
  composable("subjects") { SubjectsScreen(viewModel){navController.popBackStack()} }
  composable("timer") { TimerScreen(viewModel.currentSubject,viewModel.currentTopic,{m->viewModel.logCompletedSession(viewModel.currentSubject,viewModel.currentTopic,m);navController.popBackStack()},{navController.popBackStack()}) }
  listOf("teacher","quiz","examiner","progress","library","report").forEach { route -> composable(route) { FeatureScreen(route){navController.popBackStack()} } }
 } } } }
}