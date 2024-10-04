export interface ISchedule {
    day: string;
    class_data: {
      course?: string;
      time: string;
      room: string;
    }[];
  }