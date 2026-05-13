/*
    Migration: rebuild dbo.TaskFollowLog so LogID is INT IDENTITY(1,1).

    Why:
    - The backend can insert TaskFollowLog without LogID when LogID is IDENTITY.
    - If production has LogID as a plain INT NOT NULL, the backend fallback uses
      SELECT MAX(LogID) + 1, which is slower and unsafe under concurrent writes.

    Run on the SERVER production database during a maintenance window.
*/

SET XACT_ABORT ON;
GO

IF OBJECT_ID('dbo.TaskFollowLog', 'U') IS NULL
BEGIN
    RAISERROR('dbo.TaskFollowLog does not exist.', 16, 1);
END
GO

IF COLUMNPROPERTY(OBJECT_ID('dbo.TaskFollowLog'), 'LogID', 'IsIdentity') = 1
BEGIN
    PRINT 'dbo.TaskFollowLog.LogID is already IDENTITY. No rebuild needed.';

    IF NOT EXISTS (
        SELECT 1
        FROM sys.indexes
        WHERE name = 'IX_TaskFollowLog_TaskID_CreatedAt'
          AND object_id = OBJECT_ID('dbo.TaskFollowLog')
    )
    BEGIN
        CREATE INDEX IX_TaskFollowLog_TaskID_CreatedAt
        ON dbo.TaskFollowLog(TaskID, CreatedAt DESC);
    END
END
ELSE
BEGIN
    IF OBJECT_ID('dbo.TaskFollowLog_IdentityMigration', 'U') IS NOT NULL
    BEGIN
        RAISERROR('dbo.TaskFollowLog_IdentityMigration already exists. Review and remove it before running this migration.', 16, 1);
    END

    IF EXISTS (SELECT 1 FROM dbo.TaskFollowLog WHERE LogID IS NULL)
    BEGIN
        RAISERROR('dbo.TaskFollowLog has NULL LogID values. Fix data before running this migration.', 16, 1);
    END

    IF EXISTS (
        SELECT LogID
        FROM dbo.TaskFollowLog
        GROUP BY LogID
        HAVING COUNT(*) > 1
    )
    BEGIN
        RAISERROR('dbo.TaskFollowLog has duplicate LogID values. Fix data before running this migration.', 16, 1);
    END

    BEGIN TRANSACTION;

    CREATE TABLE dbo.TaskFollowLog_IdentityMigration (
        LogID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        TaskID INT NOT NULL,
        ActionType NVARCHAR(50) NOT NULL,
        Note NVARCHAR(MAX) NULL,
        Status NVARCHAR(100) NULL,
        HandoffFromUsername NVARCHAR(100) NULL,
        HandoffFromDisplayName NVARCHAR(255) NULL,
        HandoffToType NVARCHAR(20) NULL,
        HandoffToUsername NVARCHAR(100) NULL,
        HandoffToDisplayName NVARCHAR(255) NULL,
        UpdatedByUsername NVARCHAR(100) NOT NULL,
        UpdatedByDisplayName NVARCHAR(255) NULL,
        CreatedAt DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_TaskFollowLog_IdentityMigration_TaskID
            FOREIGN KEY (TaskID) REFERENCES dbo.TaskFollow(TaskID)
    );

    SET IDENTITY_INSERT dbo.TaskFollowLog_IdentityMigration ON;

    INSERT INTO dbo.TaskFollowLog_IdentityMigration
    (
        LogID,
        TaskID,
        ActionType,
        Note,
        Status,
        HandoffFromUsername,
        HandoffFromDisplayName,
        HandoffToType,
        HandoffToUsername,
        HandoffToDisplayName,
        UpdatedByUsername,
        UpdatedByDisplayName,
        CreatedAt
    )
    SELECT
        LogID,
        TaskID,
        ActionType,
        Note,
        Status,
        HandoffFromUsername,
        HandoffFromDisplayName,
        HandoffToType,
        HandoffToUsername,
        HandoffToDisplayName,
        UpdatedByUsername,
        UpdatedByDisplayName,
        CreatedAt
    FROM dbo.TaskFollowLog
    ORDER BY LogID;

    SET IDENTITY_INSERT dbo.TaskFollowLog_IdentityMigration OFF;

    DROP TABLE dbo.TaskFollowLog;

    EXEC sp_rename 'dbo.TaskFollowLog_IdentityMigration', 'TaskFollowLog';

    EXEC sp_rename
        'dbo.FK_TaskFollowLog_IdentityMigration_TaskID',
        'FK_TaskFollowLog_TaskID',
        'OBJECT';

    CREATE INDEX IX_TaskFollowLog_TaskID_CreatedAt
    ON dbo.TaskFollowLog(TaskID, CreatedAt DESC);

    DECLARE @max_log_id INT;
    SELECT @max_log_id = ISNULL(MAX(LogID), 0) FROM dbo.TaskFollowLog;
    DBCC CHECKIDENT ('dbo.TaskFollowLog', RESEED, @max_log_id);

    COMMIT TRANSACTION;

    PRINT 'dbo.TaskFollowLog.LogID was rebuilt as IDENTITY.';
END
GO
