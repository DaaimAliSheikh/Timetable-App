import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const saveToStorage = (value: object) => {
  localStorage.setItem("timetable-data", JSON.stringify(value));
};

const getFromStorage = () => {
  const storedData = localStorage.getItem("timetable-data");
  return storedData ? JSON.parse(storedData) : null;
};

export { saveToStorage, getFromStorage };
