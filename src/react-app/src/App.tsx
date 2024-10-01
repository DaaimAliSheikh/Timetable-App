import { useEffect, useState } from "react";
import { FiLoader } from "react-icons/fi";

interface ITimeTableDay {
  day: string;
  class_data: {
    course: string;
    time: string;
    room: string;
  }[];
}

function App() {
  const [timeTableDay, setTimeTableDay] = useState<ITimeTableDay[]>([]);
  const [day, setDay] = useState<number>(0);
  useEffect(() => {
    (async () => {
      const response = fetch("/timetable");
      const result = await (await response).json();
      setTimeTableDay(result);
    })();
  }, []);

  return (
    <div className="container">
      <h1>Time table</h1>
      <h2>{timeTableDay[day]?.day}</h2>
      <div className="btn-container">
        <button className="btn" onClick={() => day > 0 && setDay(day - 1)}>
          Previous
        </button>
        <button className="btn" onClick={() => day < 4 && setDay(day + 1)}>
          Next
        </button>
      </div>
      <ul className="class-container">
        {timeTableDay[day]?.class_data.map((day) => {
          return (
            <li>
              <h3> {day.course}</h3>
              <p> {day.room}</p>
              <p> {day.time}</p>
            </li>
          );
        }) || <FiLoader size={30} />}
      </ul>
    </div>
  );
}

export default App;
