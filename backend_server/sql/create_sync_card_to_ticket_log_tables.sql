IF OBJECT_ID('dbo.SyncCardToTicketLog', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.SyncCardToTicketLog (
        LogID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Username NVARCHAR(100) NOT NULL,
        ShopRawText NVARCHAR(255) NOT NULL,
        ShopName NVARCHAR(255) NOT NULL,
        ZipCode NVARCHAR(20) NOT NULL,
        TicketNumber NVARCHAR(100) NOT NULL,
        TicketTotalAmount DECIMAL(18,2) NULL,
        CaseType NVARCHAR(50) NULL,
        FinalGUID NVARCHAR(50) NULL,
        CardDBHId NVARCHAR(50) NULL,
        CardRefNum NVARCHAR(100) NULL,
        CardAmount DECIMAL(18,2) NULL,
        CardTipAmount DECIMAL(18,2) NULL,
        CardL4 NVARCHAR(20) NULL,
        CreatedAt DATETIME NOT NULL DEFAULT GETDATE()
    )
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_SyncCardToTicketLog_TicketNumber'
      AND object_id = OBJECT_ID('dbo.SyncCardToTicketLog')
)
BEGIN
    CREATE INDEX IX_SyncCardToTicketLog_TicketNumber
    ON dbo.SyncCardToTicketLog(TicketNumber)
END
GO
