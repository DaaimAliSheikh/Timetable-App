export default function getDayIndex() {
    const today = new Date();
    const dayOfWeek = today.getDay();
  
    // Mapping getDay() result to your Monday-Friday index (0-4)
    // 1 represents Monday, 5 represents Friday
    if (dayOfWeek >= 1 && dayOfWeek <= 5) {
      return dayOfWeek - 1; // Subtract 1 so Monday starts at 0
    } else {
      return 0; // For Saturday (6) and Sunday (0), return null or handle it as needed
    }
  }