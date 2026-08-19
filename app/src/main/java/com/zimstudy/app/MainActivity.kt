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
import com.zimstudy.app.ui.DashboardScreen
import com.zimstudy.app.ui.OnboardingScreen
import com.zimstudy.app.ui.SubjectsScreen
import com.zimstudy.app.ui.TimerScreen

class MainActivity : ComponentActivity() {

    private val viewModel: StudyViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    val navController = rememberNavController()
                    val profile by viewModel.profile.collectAsState()

                    NavHost(
                        navController = navController,
                        startDestination = if (profile == null) "onboarding" else "dashboard"
                    ) {
                        composable("onboarding") {
                            OnboardingScreen(
                                onComplete = { name, school, grade, board, year ->
                                    viewModel.saveProfile(name, school, grade, board, year)
                                    navController.navigate("dashboard") {
                                        popUpTo("onboarding") { inclusive = true }
                                    }
                                }
                            )
                        }
                        composable("dashboard") {
                            DashboardScreen(
                                viewModel = viewModel,
                                onOpenSubjects = { navController.navigate("subjects") },
                                onStartTimer = { subject, topic ->
                                    viewModel.startSession(subject, topic)
                                    navController.navigate("timer")
                                }
                            )
                        }
                        composable("subjects") {
                            SubjectsScreen(viewModel = viewModel, onBack = { navController.popBackStack() })
                        }
                        composable("timer") {
                            TimerScreen(
                                subject = viewModel.currentSubject,
                                topic = viewModel.currentTopic,
                                onSessionComplete = { minutes ->
                                    viewModel.logCompletedSession(
                                        viewModel.currentSubject,
                                        viewModel.currentTopic,
                                        minutes
                                    )
                                    navController.popBackStack("dashboard", inclusive = false)
                                },
                                onCancel = { navController.popBackStack() }
                            )
                        }
                    }
                }
            }
        }
    }
}
