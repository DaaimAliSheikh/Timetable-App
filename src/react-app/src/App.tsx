import { useEffect, useState } from "react";
import { FiLoader } from "react-icons/fi";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ClassroomList from "./components/ui/ClassroomList";

import type { ISchedule } from "@/types";
import extractSheetId from "./lib/extractSheetId";
import getDayIndex from "./lib/getDayIndex";
import { saveToStorage, getFromStorage } from "./lib/utils";

let static_section: string;

function App() {
  const [timeTable, setTimeTable] = useState<ISchedule[]>([]);
  const [freeClasses, setFreeClasses] = useState<ISchedule[]>([]);
  const [sheetLink, setSheetLink] = useState<string>("");
  const [section, setSection] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [dayIndex, setDayIndex] = useState<number>(getDayIndex());
  useEffect(() => {
    (async () => {
      try {
        if (!getFromStorage()) {
          const response = await fetch("/timetable");
          if (!response.ok) {
            const errorData = await response.json();
            return setErrorMessage(errorData.detail);
          }
          saveToStorage(await response.json());
        }
        const result = getFromStorage();

        setTimeTable(result.time_table);
        setSheetLink(result.url);
        setSection(result.section);
        setFreeClasses(result.free_classes);
        setErrorMessage("");
        static_section = result.section;
      } catch (error: any) {
        setErrorMessage("Network error");
      }
    })();
  }, []);

  return (
    <div className="flex flex-col px-3 items-center w-full max-w-[20rem] mx-auto">
      <p className="w-[100vw] sticky top-0 z-10 border-b-2 border-blue-500 text-sm py-1 mb-2 bg-[#1a1a1a] text-center">
        Made by
        <a
          href="https://github.com/DaaimAliSheikh"
          target="_blank"
          className="bg-gradient-to-r from-blue-400 to-blue-700 bg-clip-text text-transparent"
        >
          {" "}
          Daaim Ali Sheikh{" "}
        </a>
        🥶
      </p>
      <h1 className="text-xl font-bold  my-3">FAST NUCES KHI Timetable</h1>
      <div className="flex  w-full mb-1 flex-col  text-start">
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
              saveToStorage(result);

              setTimeTable(result.time_table);
              setFreeClasses(result.free_classes);
              setErrorMessage("");
              static_section = result.section;
            } catch (error: any) {
              setErrorMessage("Network error");
            }
            setLoading(false);
          }}
          className="flex flex-col gap-1 my-1"
        >
          <h2 className="text-sm ">Current Google Sheets link:</h2>

          <input
            className="w-full text-sm p-1 rounded-md"
            type="text"
            value={sheetLink}
            onChange={(e) => setSheetLink(e.target.value)}
          />

          <h2 className="text-sm mt-1">Enter your section:</h2>
          <input
            className="w-full text-sm p-1 rounded-md"
            type="text"
            value={section}
            onChange={(e) => setSection(e.target.value)}
            placeholder="eg: BCS-5G"
          />
          <button type="submit" className="py-1 my-1 flex justify-center">
            {loading ? (
              <FiLoader size={18} className="animate-spin m-1" />
            ) : (
              "Update classes"
            )}
          </button>
        </form>

        <p className="text-red-500">{errorMessage}</p>
      </div>
      <Tabs defaultValue="time_table" className="w-full">
        <TabsList className="w-full grid grid-cols-2 gap-1 rounded-sm">
          <TabsTrigger
            className="data-[state=active]:bg-blue-700 data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-blue-700 rounded-sm"
            value="time_table"
          >
            Time Table
          </TabsTrigger>
          <TabsTrigger
            className="data-[state=active]:bg-blue-700 data-[state=active]:bg-gradient-to-r data-[state=active]:from-blue-500 data-[state=active]:to-blue-700 rounded-sm"
            value="free_classes"
          >
            Free Classes
          </TabsTrigger>
        </TabsList>
        <TabsContent value="time_table">
          <ClassroomList
            schedule={timeTable}
            setDayIndex={setDayIndex}
            dayIndex={dayIndex}
            static_section={static_section}
          />
        </TabsContent>
        <TabsContent value="free_classes">
          <ClassroomList
            schedule={freeClasses}
            setDayIndex={setDayIndex}
            dayIndex={dayIndex}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default App;
