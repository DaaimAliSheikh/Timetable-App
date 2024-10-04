export default function extractSheetId(url: string): string | null {
    // Regular expression to match the Google Sheets document ID
    const regex = /\/d\/([a-zA-Z0-9-_]+)\//;
    const match = url.match(regex);
  
    // Return the extracted ID or null if not found
    return match ? match[1] : null;
  }