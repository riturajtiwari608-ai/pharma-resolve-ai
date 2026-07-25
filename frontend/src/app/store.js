import { configureStore } from "@reduxjs/toolkit";

import complaintReducer from "../features/complaints/complaintSlice";

export const store = configureStore({
  reducer: {
    complaints: complaintReducer,
  },

  devTools: import.meta.env.DEV,
});