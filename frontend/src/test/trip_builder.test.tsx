import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NewTripPage } from "../pages/NewTripPage";

const queryClient = new QueryClient();

describe("Smart Trip Builder (/trips/new)", () => {
  it("renders step 1 form inputs correctly", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NewTripPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    expect(screen.getByText("Where & When")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e.g. Rajasthan Heritage Getaway/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e.g. Udaipur, India/i)).toBeInTheDocument();
    expect(screen.getByText("Next Step")).toBeInTheDocument();
  });
});
