import { useEffect, useState } from "react";
import { CiNoWaitingSign } from "react-icons/ci";
import { FaChevronCircleLeft, FaChevronCircleRight } from "react-icons/fa";
import { FiLoader } from "react-icons/fi";

interface ITimeTable {
  day: string;
  class_data: {
    course: string;
    time: string;
    room: string;
  }[];
}

function extractSheetId(url: string): string | null {
  // Regular expression to match the Google Sheets document ID
  const regex = /\/d\/([a-zA-Z0-9-_]+)\//;
  const match = url.match(regex);

  // Return the extracted ID or null if not found
  return match ? match[1] : null;
}

let static_section: string;

function App() {
  const [timeTable, setTimeTable] = useState<ITimeTable[]>([]);
  const [sheetLink, setSheetLink] = useState<string>("");
  const [section, setSection] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [day, setDay] = useState<number>(0);
  useEffect(() => {
    (async () => {
      try {
        const response = await fetch("/timetable");
        if (!response.ok) {
          const errorData = await response.json();
          return setErrorMessage(errorData.detail);
        }
        const result = await response.json();

        setTimeTable(result.time_table);
        setSheetLink(result.url);
        setSection(result.section);
        setErrorMessage("");
        static_section = result.section;
      } catch (error: any) {
        setErrorMessage("Network error");
      }
    })();
  }, []);

  return (
    <div className="flex flex-col px-3 items-center w-full max-w-[20rem] mx-auto">
      <p className="w-full text-sm py-1 mb-2 bg-[#1a1a1a] text-center">
        Made by
        <span className="bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">
          {" "}
          Daaim Ali Sheikh{" "}
        </span>
        🥶
      </p>
      <h1 className="text-2xl">FAST NUCES KHI Timetable</h1>
      <div className="flex my-2 w-full flex-col  text-start">
        <form
          onSubmit={async (e) => {
            setLoading(true);
            e.preventDefault();
            try {
              const response = await fetch(
                "/timetable?sheetId=" +
                  extractSheetId(sheetLink) +
                  "&section=" +
                  (section || "XXX")
              );
              if (!response.ok) {
                const errorData = await response.json();
                setErrorMessage(errorData.detail);
                setLoading(false);
                return;
              }
              const result = await response.json();

              setTimeTable(result.time_table);
              setErrorMessage("");
              static_section = result.section;
            } catch (error: any) {
              setErrorMessage("Network error");
            }
            setLoading(false);
          }}
          className="flex flex-col gap-2 my-1"
        >
          <h2>Current Google Sheets link:</h2>

          <input
            className="w-full p-1"
            type="text"
            value={sheetLink}
            onChange={(e) => setSheetLink(e.target.value)}
          />

          <h2>Current section:</h2>
          <input
            className="w-full p-1"
            type="text"
            value={section}
            onChange={(e) => setSection(e.target.value)}
            placeholder="eg: BCS-5G"
          />
          <button type="submit" className="py-1 flex justify-center">
            {loading ? (
              <FiLoader size={20} className="animate-spin m-1" />
            ) : (
              "update"
            )}
          </button>
        </form>

        <p className="text-red-500">{errorMessage}</p>
      </div>

      <div className="justify-between w-full items-center my-2 flex">
        <button
          className="rounded-full"
          onClick={() => day > 0 && setDay(day - 1)}
        >
          <FaChevronCircleLeft />
        </button>
        <div className="text-center">
          <h2 className="text-xl font-bold mx-4">{timeTable[day]?.day}</h2>
          <p className="text-sm">{static_section}</p>
        </div>
        <button
          className="rounded-full"
          onClick={() => day < 4 && setDay(day + 1)}
        >
          <FaChevronCircleRight />
        </button>
      </div>
      <ul className="flex flex-col gap-6 my-4 text-center">
        {timeTable.length === 0 ? (
          <FiLoader className="animate-spin" size={30} />
        ) : timeTable[day]?.class_data.length > 0 ? (
          timeTable[day]?.class_data.map((day, index) => {
            return (
              <li key={index} className=" bg-[#1a1a1a] p-2 rounded-md text-sm">
                <h3 className="font-bold text-lg mb-1 leading-6">
                  {" "}
                  {day.course}
                </h3>
                <p> {day.room}</p>
                <p> {day.time}</p>
              </li>
            );
          })
        ) : (
          <div className=" text-center  my-2">
            <CiNoWaitingSign className="mx-auto" size={30} />
            <p>No classes on this day!</p>
          </div>
        )}
      </ul>
    </div>
  );
}

export default App;
