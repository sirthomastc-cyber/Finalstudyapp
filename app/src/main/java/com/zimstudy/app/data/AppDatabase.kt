package com.zimstudy.app.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [StudentProfile::class, SubjectEntity::class, ExamEntry::class, StudySession::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun studentProfileDao(): StudentProfileDao
    abstract fun subjectDao(): SubjectDao
    abstract fun examEntryDao(): ExamEntryDao
    abstract fun studySessionDao(): StudySessionDao

    companion object {
        @Volatile private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "zimstudy.db"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}
