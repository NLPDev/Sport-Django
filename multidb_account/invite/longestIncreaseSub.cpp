#include <iostream>
#include <vector>
using namespace std;

// Iterative function to find longest increasing subsequence
// of given array
void findLIS(int arr[], int n)
{
	// LIS[i] stores the longest increasing subsequence of subarray
	// arr[0..i] that ends with arr[i]
	vector<int> LIS[n];

	// LIS[0] denotes longest increasing subsequence ending with arr[0]
	LIS[0].push_back(arr[0]);

	// start from second element in the array
	for (int i = 1; i < n; i++)
	{
		// do for each element in subarray arr[0..i-1]
		for (int j = 0; j < i; j++)
		{
			// find longest increasing subsequence that ends with arr[j]
			// where arr[j] is less than the current element arr[i]

			if (arr[j] < arr[i] && LIS[j].size() > LIS[i].size())
				LIS[i] = LIS[j];
		}

		// include arr[i] in LIS[i]
		LIS[i].push_back(arr[i]);
	}

	// uncomment below lines to print contents of vector LIS
	/* for (int i = 0; i < n; i++)
	{
		cout << "LIS[" << i << "] - ";
		for (int j : LIS[i])
			cout << j << " ";
		cout << endl;
	} */

	// j will contain index of LIS
	int j;
	for (int i = 0; i < n; i++)
		if (LIS[j].size() < LIS[i].size())
			j = i;

	// print LIS
	for (int i : LIS[j])
		cout << i << " ";
}

// main function
int main()
{
	int arr[] = { 0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15 };
	int n = sizeof(arr)/sizeof(arr[0]);

	findLIS(arr, n);

	return 0;
}