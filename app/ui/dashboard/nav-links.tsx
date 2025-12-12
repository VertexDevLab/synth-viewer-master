"use client";

import {
  UserGroupIcon,
  HomeIcon,
  TableCellsIcon,
  UserIcon,
  Bars4Icon,
  ChartBarIcon,
} from "@heroicons/react/24/outline";
import axios from "axios";
import Link from "next/link";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { MY_UIDS } from "@/app/config";

// Map of links to display in the side navigation.
// Depending on the size of the application, this would be stored in a database.
const links = [
  { name: "Home", href: "/dashboard", icon: HomeIcon },
  { name: "Latest Scores", href: "/score/latest", icon: Bars4Icon },
  {
    name: "Historical Scores",
    href: "/score/historical",
    icon: ChartBarIcon,
  },
  {
    name: "Performance",
    href: "/performance",
    icon: ChartBarIcon,
  },
  ...MY_UIDS.map(({ uid, label }) => ({
    name: label,
    href: `/miner/${uid}`,
    icon: UserIcon,
  })),
];

export default function NavLinks() {
  const pathname = usePathname();
  const [minerRunning, setMinerRunning] = useState<Record<string, boolean>>({});

  const getMinerResponse = async (minerUid: string) => {
    try {
      const res = await axios.get(
        `https://synth.mode.network/validation/miner?uid=${minerUid}`
      );
      if (res.data.validated) {
        setMinerRunning((prev) => ({ ...prev, [minerUid]: true }));
      }
    } catch (error) {
      console.error(error);
      setMinerRunning((prev) => ({ ...prev, [minerUid]: false }));
    }
  };
  useEffect(() => {
    // Function to fetch all miners
    const fetchAllMiners = () => {
      MY_UIDS.forEach(({ uid }) => getMinerResponse(uid.toString()));
    };

    // Fetch immediately on component mount
    fetchAllMiners();

    // Set up interval to fetch every 5 minute
    const intervalId = setInterval(fetchAllMiners, 300000);

    // Cleanup interval on component unmount
    return () => clearInterval(intervalId);
  }, []);

  return (
    <>
      {links.map((link) => {
        const LinkIcon = link.icon;
        return (
          <Link
            key={link.name}
            href={link.href}
            className={`flex h-[48px] items-center justify-between w-full gap-2 rounded-md bg-gray-50 p-3 text-sm font-medium hover:bg-sky-100 hover:text-blue-600 md:flex-none md:p-2 md:px-3 ${
              pathname === link.href ? `bg-sky-100 text-blue-600` : ``
            }`}
          >
            <div className="flex items-center gap-2">
              <LinkIcon className="w-6" />
              <p className="hidden md:block text-xs">
                {isNaN(Number(link.name))
                  ? link.name
                  : "X" + link.name.slice(1)}
              </p>
            </div>
            {link.name.startsWith("Neuron") ? (
              minerRunning[link.name.split(" ")[1]] ? (
                <div className="w-[12px] h-[12px] relative">
                  <div className="absolute inset-0 bg-green-500 rounded-full animate-[bubble_2s_ease-in-out_infinite_0.5s]"></div>
                </div>
              ) : (
                <div className="w-[12px] h-[12px] bg-red-500 rounded-full"></div>
              )
            ) : null}
          </Link>
        );
      })}
    </>
  );
}
