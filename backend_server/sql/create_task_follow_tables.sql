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
