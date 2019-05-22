

#include "CLI11.hpp"
#include <cstdlib>
#include <cstdio>
#include <chrono>

int _sequenceSize;
std::string _algorithm;
std::string _sequenceType;
unsigned long _seed;
int _lowerBound;
int _upperBound;
int _runs;
std::string _outputTemplate;

int generateRandomNumber(int lb, int ub, bool lbIn, bool ubIn) {
    lb += lbIn ? 0: 1;
    ub += ubIn ? 1: 0;
    if (lb > ub) {
        throw std::domain_error{"cannot generate random number"};
    }
    return lb + (rand() % (ub - lb)); 
}

std::vector<int> generateRandomSequence(int size) {
    std::vector<int> result{size};
    for (int i=0; i<size; ++i) {
        result.push_back(generateRandomNumber(_lowerBound, _upperBound, true, true));
    }
    return result;
}

std::vector<int> generateSameSequence(int size) {
    std::vector<int> result{size};
    int x = generateRandomNumber(_lowerBound, _upperBound, true, true);
    for (int i=0; i<size; ++i) {
        result.push_back(x);
    }
    return result;
}

std::vector<int> generateSortedSequence(int size) {
    std::vector<int> result{size};
    for (int i=0; i<size; ++i) {
        result.push_back(_lowerBound + i);
    }
    return result;
}

std::vector<int> generateReverseSortedSequence(int size) {
    std::vector<int> result{size};
    for (int i=0; i<size; ++i) {
        result.push_back(_upperBound - i);
    }
    return result;
}

class ISortAlgorithm {
public:
    virtual ~ISortAlgorithm() {

    }
    virtual std::vector<int>& sort(std::vector<int>& sequence) = 0;
    virtual void reset() = 0;
    bool validateSequence(const std::vector<int>& sequence) const {
        int previous;
        bool first = true;
        for (int i=0; i<sequence.size(); ++i) {
            if (first) {
                previous = sequence[i];
            } else {
                if (sequence[i] < previous) {
                    return false;
                }
                previous = sequence[i];
            }
        }
        return true;
    }
};


class BubbleSort : public ISortAlgorithm {
public:
    BubbleSort() {}
    virtual ~BubbleSort() {}
    virtual void reset() {

    }
    std::vector<int>& sort(std::vector<int>& sequence) {
    for (int i=0; i<(sequence.size()-1); ++i) {
        for (int j=(i+1); j<sequence.size(); ++j) {
            if (sequence[i] > sequence[j]) {
                int tmp = sequence[i];
                sequence[i] = sequence[j];
                sequence[j] = tmp;
            }
        }
    }
    return sequence;
}
};

class MergeSort : public ISortAlgorithm {
public:
    MergeSort() {}
    virtual ~MergeSort() {}
    virtual void reset() {}
    std::vector<int>& sort(std::vector<int>& sequence) {
        this->_merge(sequence, 0, sequence.size());
        return sequence;
    }
private:
    void merge(std::vector<int>& sequence, int left, int middle, int right) {
        int i, j, k; 
        int n1 = middle - left + 1; 
        int n2 =  right - middle; 
    
        /* create temp arrays */
        int L[n1], R[n2]; 
    
        /* Copy data to temp arrays L[] and R[] */
        for (i = 0; i < n1; i++) {
            L[i] = sequence[left + i]; 
        }
        for (j = 0; j < n2; j++) {
            R[j] = sequence[middle + 1+ j]; 
        }
    
        /* Merge the temp arrays back into arr[l..r]*/
        i = 0; // Initial index of first subarray 
        j = 0; // Initial index of second subarray 
        k = left; // Initial index of merged subarray 
        while (i < n1 && j < n2) { 
            if (L[i] <= R[j]) { 
                sequence[k] = L[i]; 
                i++; 
            } else { 
                sequence[k] = R[j]; 
                j++; 
            } 
            k++; 
        } 
    
        /* Copy the remaining elements of L[], if there 
        are any */
        while (i < n1) { 
            sequence[k] = L[i]; 
            i++; 
            k++; 
        } 
    
        /* Copy the remaining elements of R[], if there 
        are any */
        while (j < n2) { 
            sequence[k] = R[j]; 
            j++; 
            k++; 
        } 
    }

    void _merge(std::vector<int>& sequence, int left, int right) {
        if (right > left) {
            return;
        }

        int middle = left + (right - left)/2;
        
        this->_merge(sequence, left, middle);
        this->_merge(sequence, middle + 1, right);

        this->merge(sequence, left, middle, right);
    }
};

int main(const int argc, const char* args[]) {

    CLI::App app{"Sorting algorithm tester"};

    app.add_option("--sequenceSize", _sequenceSize, "Size of the array to sort");
    app.add_option("--sequenceType", _sequenceType, "type of the sequence to sort: RANDOM, SAME, SORTED, REVERSESORTED");
    app.add_option("--algorithm", _algorithm, "algorithm to test. BUBBLESORT, MERGESORT");
    app.add_option("--lowerBound", _lowerBound, "Minimum number we might generate");
    app.add_option("--upperBound", _upperBound, "Maximum number we might generate");
    app.add_option("--runs", _runs, "Number of run we need to perform (execution of the same trial)");
    app.add_option("--seed", _seed, "Seed for random generator");
    app.add_option("--outputTemplate", _outputTemplate);

    CLI11_PARSE(app, argc, args);

    srand(_seed);

    ISortAlgorithm* alg = nullptr;
    if (_algorithm == std::string{"BUBBLESORT"}) {
        alg = new BubbleSort{};
    } else if (_algorithm == std::string{"MERGESORT"}) {
        alg = new MergeSort{};
    } else {
        throw std::domain_error{"invalid algorithm!"};
    }

    std::string csvFileName{_outputTemplate};
    csvFileName.append("kind:type=main|.csv");
    FILE* f = fopen(csvFileName.c_str(), "w");
    if (f == NULL) {
        throw std::domain_error{"can't open file"};
    }
    fprintf(f, "run,time\n");

    for (int run=0; run<_runs; ++run) {
        std::vector<int> sequence{};

        if (_sequenceType == std::string{"RANDOM"}) {
            sequence = generateRandomSequence(_sequenceSize);
        } else if (_sequenceType == std::string{"SAME"}) {
            sequence = generateSameSequence(_sequenceSize);
        } else if (_sequenceType == std::string{"SORTED"}) {
            sequence = generateSortedSequence(_sequenceSize);
        } else if (_sequenceType == std::string{"REVERSESORTED"}) {
            sequence = generateReverseSortedSequence(_sequenceSize);
        } else{
            throw std::domain_error{"invalid type!"};
        }

        alg->reset();
        auto start = std::chrono::system_clock::now();
        alg->sort(sequence);
        auto end = std::chrono::system_clock::now();
        std::chrono::duration<double> elapsed_seconds = end-start;

        if (!alg->validateSequence(sequence)) {
            throw std::domain_error{"sorting failed!"};
        }

        fprintf(f, "%d,%d\n", run, static_cast<int>(1e6 * elapsed_seconds.count()));
    }

    fclose(f);
    
    delete alg;

}
