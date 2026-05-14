"use client";

import { useDispatch, useSelector, useStore } from "react-redux";
import type { AppDispatch, RootState } from "./store";

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector = <TSelected>(
  selector: (state: RootState) => TSelected
) => useSelector(selector);
export const useAppStore = () => useStore<RootState>();
