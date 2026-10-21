import { QueryCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, displayError } from "@/lib/api-client";
export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) =>
      toast.error(displayError(error), { id: query.queryHash }),
  }),
  defaultOptions: {
    queries: {
      retry: (count, error) =>
        !(error instanceof ApiError && error.status < 500) && count < 1,
      staleTime: 30000,
    },
    mutations: { retry: false },
  },
});
