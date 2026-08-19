package com.zimstudy.app

import android.app.Application
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.zimstudy.app.data.AppDatabase
import com.zimstudy.app.data.ExamEntry
import com.zimstudy.app.data.StudentProfile
import com.zimstudy.app.data.StudySession
import com.zimstudy.app.data.SubjectEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class StudyViewModel(application: Application) : AndroidViewModel(application) {

    private val db = AppDatabase.getInstance(application)
    private val profileDao = db.studentProfileDao()
    private val subjectDao = db.subjectDao()
    private val examDao = db.examEntryDao()
    private val sessionDao = db.studySessionDao()

    val profile = profileDao.getProfile()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    val subjects = subjectDao.getAllSubjects()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val exams = examDao.getAllExams()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Holds which subject/topic the user is about to study, set right before
    // navigating to the timer screen.
    var currentSubject by mutableStateOf("General")
        private set
    var currentTopic by mutableStateOf("Study Session")
        private set

    fun startSession(subject: String, topic: String) {
        currentSubject = subject
        currentTopic = topic
    }

    fun saveProfile(name: String, school: String, grade: String, examBoard: String, examYear: String) {
        viewModelScope.launch {
            profileDao.saveProfile(StudentProfile(1, name, school, grade, examBoard, examYear))
        }
    }

    fun addSubject(name: String) {
        if (name.isBlank()) return
        viewModelScope.launch { subjectDao.addSubject(SubjectEntity(name = name.trim())) }
    }

    fun deleteSubject(subject: SubjectEntity) {
        viewModelScope.launch { subjectDao.deleteSubject(subject) }
    }

    fun addExam(subjectName: String, paperNumber: String, examDateMillis: Long) {
        viewModelScope.launch {
            examDao.addExam(ExamEntry(subjectName = subjectName, paperNumber = paperNumber, examDateMillis = examDateMillis))
        }
    }

    fun logCompletedSession(subjectName: String, topic: String, durationMinutes: Int) {
        viewModelScope.launch {
            sessionDao.addSession(
                StudySession(
                    subjectName = subjectName,
                    topic = topic,
                    startedAtMillis = System.currentTimeMillis(),
                    durationMinutes = durationMinutes,
                    completed = true
                )
            )
        }
    }
}
