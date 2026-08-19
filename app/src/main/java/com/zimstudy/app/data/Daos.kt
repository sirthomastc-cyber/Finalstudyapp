package com.zimstudy.app.data

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface StudentProfileDao {
    @Query("SELECT * FROM student_profile WHERE id = 1")
    fun getProfile(): Flow<StudentProfile?>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun saveProfile(profile: StudentProfile)
}

@Dao
interface SubjectDao {
    @Query("SELECT * FROM subjects ORDER BY name")
    fun getAllSubjects(): Flow<List<SubjectEntity>>

    @Insert
    suspend fun addSubject(subject: SubjectEntity)

    @Delete
    suspend fun deleteSubject(subject: SubjectEntity)
}

@Dao
interface ExamEntryDao {
    @Query("SELECT * FROM exam_entries ORDER BY examDateMillis")
    fun getAllExams(): Flow<List<ExamEntry>>

    @Insert
    suspend fun addExam(exam: ExamEntry)

    @Delete
    suspend fun deleteExam(exam: ExamEntry)
}

@Dao
interface StudySessionDao {
    @Query("SELECT * FROM study_sessions ORDER BY startedAtMillis DESC")
    fun getAllSessions(): Flow<List<StudySession>>

    @Insert
    suspend fun addSession(session: StudySession): Long

    @Update
    suspend fun updateSession(session: StudySession)
}
