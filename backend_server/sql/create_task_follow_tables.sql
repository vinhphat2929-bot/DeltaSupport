IF OBJECT_ID('dbo.TaskFollow', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TaskFollow (
        TaskID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        TaskDate DATE NULL,
        MerchantRawText NVARCHAR(255) NOT NULL,
        MerchantName NVARCHAR(255) NOT NULL,
        ZipCode NVARCHAR(20) NULL,
        Phone NVARCHAR(20) NULL,
        ProblemSummary NVARCHAR(1000) NULL,
        HandoffFromUsername NVARCHAR(100) NULL,
        HandoffFromDisplayName NVARCHAR(255) NULL,
        HandoffToType NVARCHAR(20) NULL,
        HandoffToUsername NVARCHAR(100) NULL,
        HandoffToDisplayName NVARCHAR(255) NULL,
        Status NVARCHAR(100) NOT NULL,
        DeadlineDate DATE NULL,
        DeadlineTime TIME NULL,
        CurrentNote NVARCHAR(MAX) NULL,
        LastUpdatedByUsername NVARCHAR(100) NULL,
        LastUpdatedByDisplayName NVARCHAR(255) NULL,
        CreatedAt DATETIME NOT NULL DEFAULT GETDATE(),
        UpdatedAt DATETIME NOT NULL DEFAULT GETDATE(),
        IsActive BIT NOT NULL DEFAULT 1
    )
END
GO

IF COL_LENGTH('dbo.TaskFollow', 'TrainingFormJson') IS NULL
BEGIN
    ALTER TABLE dbo.TaskFollow
    ADD TrainingFormJson NVARCHAR(MAX) NULL
END
GO

IF COL_LENGTH('dbo.TaskFollow', 'TrainingStartedAt') IS NULL
BEGIN
    ALTER TABLE dbo.TaskFollow
    ADD TrainingStartedAt DATETIME NULL
END
GO

IF COL_LENGTH('dbo.TaskFollow', 'TrainingStartedByUsername') IS NULL
BEGIN
    ALTER TABLE dbo.TaskFollow
    ADD TrainingStartedByUsername NVARCHAR(100) NULL
END
GO

IF COL_LENGTH('dbo.TaskFollow', 'TrainingStartedByDisplayName') IS NULL
BEGIN
    ALTER TABLE dbo.TaskFollow
    ADD TrainingStartedByDisplayName NVARCHAR(255) NULL
END
GO

IF OBJECT_ID('dbo.TaskFollowLog', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TaskFollowLog (
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
        CONSTRAINT FK_TaskFollowLog_TaskID
            FOREIGN KEY (TaskID) REFERENCES dbo.TaskFollow(TaskID)
    )
END
GO

IF OBJECT_ID('dbo.TaskFollowNotificationRead', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TaskFollowNotificationRead (
        ReadID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        TaskID INT NOT NULL,
        Username NVARCHAR(100) NOT NULL,
        ReadAt DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_TaskFollowNotificationRead_TaskID
            FOREIGN KEY (TaskID) REFERENCES dbo.TaskFollow(TaskID)
    )
END
GO

IF OBJECT_ID('dbo.TaskFollowRecipient', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TaskFollowRecipient (
        RecipientID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        TaskID INT NOT NULL,
        RecipientType NVARCHAR(20) NOT NULL,
        Username NVARCHAR(100) NULL,
        DisplayName NVARCHAR(255) NULL,
        CreatedAt DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_TaskFollowRecipient_TaskID
            FOREIGN KEY (TaskID) REFERENCES dbo.TaskFollow(TaskID)
    )
END
GO

IF OBJECT_ID('dbo.TaskFollowNotificationDismiss', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.TaskFollowNotificationDismiss (
        DismissID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        TaskID INT NOT NULL,
        Username NVARCHAR(100) NOT NULL,
        DismissedAt DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_TaskFollowNotificationDismiss_TaskID
            FOREIGN KEY (TaskID) REFERENCES dbo.TaskFollow(TaskID)
    )
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_TaskFollow_Status_DeadlineDate'
      AND object_id = OBJECT_ID('dbo.TaskFollow')
)
BEGIN
    CREATE INDEX IX_TaskFollow_Status_DeadlineDate
    ON dbo.TaskFollow(Status, DeadlineDate)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_TaskFollow_MerchantName'
      AND object_id = OBJECT_ID('dbo.TaskFollow')
)
BEGIN
    CREATE INDEX IX_TaskFollow_MerchantName
    ON dbo.TaskFollow(MerchantName)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_TaskFollow_UpdatedAt'
      AND object_id = OBJECT_ID('dbo.TaskFollow')
)
BEGIN
    CREATE INDEX IX_TaskFollow_UpdatedAt
    ON dbo.TaskFollow(UpdatedAt)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_TaskFollowLog_TaskID_CreatedAt'
      AND object_id = OBJECT_ID('dbo.TaskFollowLog')
)
BEGIN
    CREATE INDEX IX_TaskFollowLog_TaskID_CreatedAt
    ON dbo.TaskFollowLog(TaskID, CreatedAt DESC)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_TaskFollowNotificationRead_TaskID_Username'
      AND object_id = OBJECT_ID('dbo.TaskFollowNotificationRead')
)
BEGIN
    CREATE UNIQUE INDEX UX_TaskFollowNotificationRead_TaskID_Username
    ON dbo.TaskFollowNotificationRead(TaskID, Username)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_TaskFollowNotificationRead_Username_ReadAt'
      AND object_id = OBJECT_ID('dbo.TaskFollowNotificationRead')
)
BEGIN
    CREATE INDEX IX_TaskFollowNotificationRead_Username_ReadAt
    ON dbo.TaskFollowNotificationRead(Username, ReadAt DESC)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_TaskFollowRecipient_TaskID'
      AND object_id = OBJECT_ID('dbo.TaskFollowRecipient')
)
BEGIN
    CREATE INDEX IX_TaskFollowRecipient_TaskID
    ON dbo.TaskFollowRecipient(TaskID)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_TaskFollowRecipient_Username'
      AND object_id = OBJECT_ID('dbo.TaskFollowRecipient')
)
BEGIN
    CREATE INDEX IX_TaskFollowRecipient_Username
    ON dbo.TaskFollowRecipient(Username)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'UX_TaskFollowNotificationDismiss_TaskID_Username'
      AND object_id = OBJECT_ID('dbo.TaskFollowNotificationDismiss')
)
BEGIN
    CREATE UNIQUE INDEX UX_TaskFollowNotificationDismiss_TaskID_Username
    ON dbo.TaskFollowNotificationDismiss(TaskID, Username)
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_TaskFollowNotificationDismiss_Username_DismissedAt'
      AND object_id = OBJECT_ID('dbo.TaskFollowNotificationDismiss')
)
BEGIN
    CREATE INDEX IX_TaskFollowNotificationDismiss_Username_DismissedAt
    ON dbo.TaskFollowNotificationDismiss(Username, DismissedAt DESC)
END
GO
