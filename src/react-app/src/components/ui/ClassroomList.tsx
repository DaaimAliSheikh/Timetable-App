import { CiNoWaitingSign } from "react-icons/ci";
import { FaChevronCircleLeft, FaChevronCircleRight } from "react-icons/fa";
import { FiLoader } from "react-icons/fi";
import type { ISchedule } from "@/types";
import { type CarouselApi } from "@/components/ui/carousel";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
} from "@/components/ui/carousel";
import { useEffect, useState } from "react";

const ClassroomList = ({
  schedule,
  dayIndex,
  setDayIndex,
  static_section,
}: {
  schedule: ISchedule[];
  dayIndex: number;
  setDayIndex: React.Dispatch<React.SetStateAction<number>>;
  static_section?: string;
}) => {
  const [api, setApi] = useState<CarouselApi>();

  // State for controlled input
  const [inputValue, setInputValue] = useState("");

  // Trigger scroll on input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
  };

  useEffect(() => {
    ///needed because "init" event is not triggered on first render
    if (!api) {
      return;
    }
    api.scrollTo(dayIndex);
  }, [api]);

  useEffect(() => {
    if (!api) {
      return;
    }

    api.on("init", () => {
      api.scrollTo(dayIndex);
    });
    api.on("select", () => {
      setDayIndex(api.selectedScrollSnap());
    });
  }, [api]);
  return (
    <>
      <div className="justify-between w-full items-center my-2 flex">
        <button
          className="rounded-full"
          onClick={() => {
            setDayIndex((prev) => {
              const newIndex = (prev - 1 + 5) % 5;
              api?.scrollTo(newIndex);
              return newIndex;
            });
          }}
        >
          <FaChevronCircleLeft />
        </button>
        <div className="text-center">
          <h2 className="text-xl font-bold mx-4">{schedule[dayIndex]?.day}</h2>
          <p className="text-sm">{static_section}</p>
        </div>
        <button
          className="rounded-full"
          onClick={() =>
            setDayIndex((prev) => {
              const newIndex = (prev + 1) % 5;
              api?.scrollTo(newIndex);
              return newIndex;
            })
          }
        >
          <FaChevronCircleRight />
        </button>
      </div>

      {schedule.length === 0 ? (
        <FiLoader className="animate-spin mx-auto" size={30} />
      ) : (
        <>
          {!!static_section || (
            <input
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              placeholder="Search for classes or timings..."
              className="border text-sm p-2 rounded-md w-full my-2"
            />
          )}

          <ScrollArea className="my-2  w-full h-[100vh] rounded-md">
            <Carousel setApi={setApi}>
              <CarouselContent className="w-full -ml-0">
                {/* CarouselContent has a default -ml set, remove it */}
                {schedule.map((class_datas, index) => {
                  return (
                    <CarouselItem key={index} className=" px-2">
                      {/* CarouselItem has default some padding left, remove or override it  */}
                      {class_datas.class_data.filter((class_info) => {
                        return (
                          class_info.time
                            .toLowerCase()
                            .includes(inputValue.toLowerCase()) ||
                          class_info.room
                            .toLowerCase()
                            .includes(inputValue.toLowerCase())
                        );
                      }).length === 0 ? (
                        <div className="flex flex-col items-center p-8">
                          <CiNoWaitingSign size={30} />
                          <p className="text-sm">No classes found!</p>
                        </div>
                      ) : (
                        <ul className=" flex flex-col  gap-2">
                          {class_datas.class_data
                            .filter((class_info) => {
                              return (
                                class_info.time
                                  .toLowerCase()
                                  .includes(inputValue.toLowerCase()) ||
                                class_info.room
                                  .toLowerCase()
                                  .includes(inputValue.toLowerCase())
                              );
                            })
                            .map((class_info, index) => {
                              return (
                                <li
                                  key={index}
                                  className={` list-item${dayIndex} bg-[#1a1a1a] p-2 text-center rounded-md text-sm`}
                                >
                                  <h3 className="font-bold text-lg mb-1 leading-6">
                                    {" "}
                                    {class_info.course}
                                  </h3>
                                  <p
                                    className={
                                      class_info.room &&
                                      "font-bold text-lg mb-1 leading-6"
                                    }
                                  >
                                    {" "}
                                    {class_info.room}
                                  </p>
                                  <p> {class_info.time}</p>
                                </li>
                              );
                            }) || "oopsie"}
                        </ul>
                      )}
                    </CarouselItem>
                  );
                })}
              </CarouselContent>
            </Carousel>
          </ScrollArea>
        </>
      )}
    </>
  );
};

export default ClassroomList;
