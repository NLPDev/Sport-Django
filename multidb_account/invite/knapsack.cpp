#include <iostream>
using namespace std;

// Input:
// Values (stored in array v)
// Weights (stored in array w)
// Number of distinct items (n)
// Knapsack capacity W
int knapSack(int v[], int w[], int n, int W)
{
	// T[i][j] stores the maximum value that can be attained with
	// weight less than or equal to j using items up to first i items
	int T[n+1][W+1];

	for (int j = 0; j <= W; j++)
		T[0][j] = 0;

	// memset (T[0], 0, sizeof T[0]);

	// do for ith item
	for (int i = 1; i <= n; i++)
	{
		// consider all weights from 0 to maximum capacity W
		for (int j = 0; j <= W; j++)
		{
			// don't include ith element if j-w[i-1] is negative
			if (w[i-1] > j)
				T[i][j] = T[i-1][j];
			else
			// find max value by excluding or including the ith item
				T[i][j] = max(T[i-1][j],
							T[i-1][j-w[i-1]] + v[i-1]);
		}
	}

	// return maximum value
	return T[n][W];
}

// 0-1 Knapsack problem
int main()
{
	// Input: set of items each with a weight and a value
	int v[] = { 20, 5, 10, 40, 15, 25 };
	int w[] = { 1, 2, 3, 8, 7, 4 };

	// Knapsack capacity
	int W = 10;

	// number of items
	int n = sizeof(v) / sizeof(v[0]);

	cout << "Knapsack value is " << knapSack(v, w, n, W);

	return 0;
}