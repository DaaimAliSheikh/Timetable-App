import { useEffect, useState } from "react";
import { FiLoader } from "react-icons/fi";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ClassroomList from "./components/ClassroomList";
import { WithContext as ReactTags, Tag } from "react-tag-input";

import type { ISchedule } from "@/types";
import extractSheetId from "./lib/extractSheetId";
import getDayIndex from "./lib/getDayIndex";
import { saveToStorage, getFromStorage } from "./lib/utils";
import { IoAddOutline } from "react-icons/io5";
import { toast } from "sonner";

function App() {
  const [timeTable, setTimeTable] = useState<ISchedule[]>([]);
  const [freeClasses, setFreeClasses] = useState<ISchedule[]>([]);
  const [sheetLink, setSheetLink] = useState<string>("");
  const [sections, setSections] = useState<Tag[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [dayIndex, setDayIndex] = useState<number>(getDayIndex());
  const [activeTab, setActiveTab] = useState("time_table");
  const [sectionValue, setSectionValue] = useState<string>("");
  const [error, setError] = useState<string>("");
  useEffect(() => {
    (async () => {
      const params = new URLSearchParams(window.location.search); // :contentReference[oaicite:2]{index=2}
      const err = params.get("error");

      if (err === "unauthorized_domain") {
        setError("Please sign in with your @nu.edu.pk email.");
        console.log("error set");
        return;
      }
      const response = await fetch("/validate", {
        credentials: "include", // send HttpOnly cookie automatically
      });
      if (!response.ok) {
        return (window.location.href = "/login");
      }

      try {
        if (!getFromStorage()) {
          const response = await fetch("/timetable", {
            method: "POST",
            body: JSON.stringify({
              sections: sections.map((section) => section.id), ///have to send data as array
            }),
            headers: {
              "Content-Type": "application/json",
            },
          });
          if (!response.ok) {
            const errorData = await response.json();
            return setErrorMessage(errorData.detail);
          }
          saveToStorage(await response.json());
        }
        const result = getFromStorage();

        setTimeTable(result.time_table);
        setSheetLink(result.url);
        setSections(
          result.sections.map((section: string) => ({
            id: section,
            text: section,
          }))
        );
        setFreeClasses(result.free_classes);
        setErrorMessage("");
      } catch (error: any) {
        setErrorMessage("Network error");
      }
    })();
  }, []);

  const handleDelete = (i: number) => {
    setSections(sections.filter((_section, index) => index !== i));
  };

  const handleAddition = (section: Tag) => {
    setSections([...sections, section]);
    setSectionValue("");
  };

  const handleDrag = (section: Tag, currPos: number, newPos: number) => {
    const newTags = sections.slice();
    newTags.splice(currPos, 1);
    newTags.splice(newPos, 0, section);
    setSections(newTags);
  };
  const onClearAll = () => {
    setSections([]);
  };
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
      {error ? (
        <div className="flex flex-col items-center justify-center gap-2">
          <p className="text-red-500 text-center">{error}</p>
          <button onClick={() => (window.location.href = "/login")}>
            Retry
          </button>
        </div>
      ) : (
        <>
          <div className="flex  w-full mb-1 flex-col  text-start">
            <form
              onSubmit={async (e) => {
                setLoading(true);
                e.preventDefault();
                try {
                  const response = await fetch(
                    "/timetable?sheetId=" + extractSheetId(sheetLink),
                    {
                      method: "POST",
                      body: JSON.stringify({
                        sections: sections.map((section) => section.id), ///have to send data as array
                      }),
                      headers: {
                        "Content-Type": "application/json",
                      },
                    }
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
                  setSections(
                    result.sections.map((section: string) => ({
                      id: section,
                      text: section,
                    }))
                  );
                  setFreeClasses(result.free_classes);
                  setErrorMessage("");
                  toast.success("Timetable updated successfully!");
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

              <h2 className="text-sm mt-1">Add Section(s):</h2>
              <div className="flex justify-start items-start ">
                <ReactTags
                  tags={sections}
                  placeholder="Eg: BCS-6G"
                  handleDelete={handleDelete}
                  handleAddition={handleAddition}
                  handleDrag={handleDrag}
                  inputFieldPosition="top"
                  autocomplete
                  clearAll
                  onClearAll={onClearAll}
                  maxTags={7}
                  handleInputChange={setSectionValue}
                  inputValue={sectionValue}
                  inline
                  editable={false}
                  allowDragDrop={false}
                  classNames={{
                    tags: "tagsClass",
                    tagInput: "tagInputClass",
                    tagInputField: "tagInputFieldClass",
                    selected: "selectedClass",
                    tag: "tagClass",
                    remove: "removeClass",
                    clearAll: "clearAllButton",
                  }}
                />
                <button
                  type="button"
                  onClick={() => {
                    sectionValue &&
                      setSections([
                        ...sections,
                        {
                          id: sectionValue,
                          className: sectionValue,
                          text: sectionValue,
                        }, ///converting string input state value to Tag
                      ]);
                    setSectionValue("");
                  }}
                  className="bg-blue-700 ml-2 p-2 rounded-md text-white"
                >
                  <IoAddOutline />
                </button>
              </div>

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
          <Tabs
            defaultValue="time_table"
            className="w-full"
            onValueChange={(value) => setActiveTab(value)}
          >
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
                sections={sections.map((section) => section.id)}
                setDayIndex={setDayIndex}
                dayIndex={dayIndex}
                activeTab={activeTab}
              />
            </TabsContent>
            <TabsContent value="free_classes">
              <ClassroomList
                schedule={freeClasses}
                setDayIndex={setDayIndex}
                dayIndex={dayIndex}
                activeTab={activeTab}
              />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}

export default App;
