import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TripDetailPage } from "../pages/TripDetailPage";

const queryClient = new QueryClient();

describe("Itinerary Viewer (/trips/:id)", () => {
  it("renders page container and back button", () => {
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <TripDetailPage />
        </BrowserRouter>
      </QueryClientProvider>
    );

    // Initial query loading state or trip not found state
    expect(screen.getByRole("link", { name: /Dashboard/i })).toBeInTheDocument();
  });
});
